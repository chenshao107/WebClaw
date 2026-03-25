"""
页面快照工具：将复杂的 HTML 转换为精简的 Markdown/Text
防止上下文爆炸，只给 LLM 看关键信息

优化点：
1. 支持预热滚动，触发懒加载
2. 智能内容提取，针对主流网站优化
3. 等待网络空闲后再抓取
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
import re
import time


@dataclass
class PageSnapshot:
    """页面快照结果"""
    url: str
    title: str
    summary: str
    links: list
    forms: list
    text_content: str
    truncated: bool = False


class PageSnapshotTool:
    """页面快照工具类"""
    
    def __init__(self, max_length: int = 8000, scroll_times: int = 3, scroll_delay: float = 0.5):
        """
        Args:
            max_length: 文本内容最大长度，超过则截断
            scroll_times: 滚动次数，用于触发懒加载
            scroll_delay: 每次滚动后的等待时间（秒）
        """
        self.max_length = max_length
        self.scroll_times = scroll_times
        self.scroll_delay = scroll_delay
    
    def _preheat_page(self, page):
        """
        预热页面：滚动触发懒加载
        
        Args:
            page: Playwright Page 对象
        """
        # 模拟滚动，强制触发懒加载
        for i in range(self.scroll_times):
            page.mouse.wheel(0, 1000)  # 向下滚 1000 像素
            time.sleep(self.scroll_delay)
        
        # 滚回顶部
        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(0.3)
    
    def capture(self, page, preheat: bool = True) -> PageSnapshot:
        """
        捕获页面快照
        
        Args:
            page: Playwright Page 对象
            preheat: 是否先滚动预热（触发懒加载）
            
        Returns:
            PageSnapshot: 页面快照
        """
        url = page.url
        title = page.title()
        
        # 预热页面（滚动触发懒加载）
        if preheat:
            self._preheat_page(page)
        
        # 获取页面主要内容（使用 JavaScript 提取）
        # 优化：针对主流网站的内容区域进行智能提取
        snapshot_data = page.evaluate("""() => {
            const result = {
                title: document.title,
                headings: [],
                links: [],
                forms: [],
                textContent: ""
            };
            
            // 提取标题层级结构
            document.querySelectorAll('h1, h2, h3, h4').forEach(h => {
                result.headings.push({
                    level: h.tagName,
                    text: h.innerText.trim().substring(0, 100)
                });
            });
            
            // 提取关键链接（只取可见的、有文本的链接）
            document.querySelectorAll('a').forEach(a => {
                const text = a.innerText.trim();
                const href = a.href;
                if (text && text.length > 0 && text.length < 50 && href && !href.startsWith('javascript:')) {
                    result.links.push({
                        text: text.substring(0, 30),
                        href: href.substring(0, 100)
                    });
                }
            });
            
            // 提取表单信息
            document.querySelectorAll('form, input, button, textarea').forEach(el => {
                const info = {
                    tag: el.tagName.toLowerCase(),
                    type: el.type || null,
                    name: el.name || null,
                    placeholder: el.placeholder || null,
                    text: el.innerText ? el.innerText.trim().substring(0, 50) : null
                };
                result.forms.push(info);
            });
            
            // 【智能内容提取】针对主流网站的内容区域
            let contentElement = null;
            
            // 尝试查找主要内容区域（按优先级）
            const contentSelectors = [
                // B站
                '.feed-matrix', '.recommended-container', '.video-list',
                // 通用
                'main', 'article', '[role="main"]',
                // 内容区域
                '.content', '.main-content', '#content', '#main',
                // 后备
                'body'
            ];
            
            for (const selector of contentSelectors) {
                const el = document.querySelector(selector);
                if (el && el.innerText.trim().length > 100) {
                    contentElement = el;
                    break;
                }
            }
            
            // 提取文本内容
            if (contentElement) {
                // 克隆节点以避免修改原页面
                const clone = contentElement.cloneNode(true);
                // 移除脚本、样式等无关元素
                clone.querySelectorAll('script, style, nav, footer, aside, iframe, noscript').forEach(el => el.remove());
                result.textContent = clone.innerText.replace(/\\s+/g, ' ').trim();
            } else {
                // 后备方案
                result.textContent = document.body.innerText.replace(/\\s+/g, ' ').trim();
            }
            
            return result;
        }""")
        
        # 截断文本内容
        text_content = snapshot_data.get("textContent", "")
        truncated = len(text_content) > self.max_length
        if truncated:
            text_content = text_content[:self.max_length] + "\n... [内容已截断]"
        
        # 生成摘要
        summary = self._generate_summary(
            title,
            snapshot_data.get("headings", []),
            len(snapshot_data.get("links", [])),
            len(snapshot_data.get("forms", []))
        )
        
        return PageSnapshot(
            url=url,
            title=title,
            summary=summary,
            links=snapshot_data.get("links", [])[:10],  # 最多10个链接
            forms=snapshot_data.get("forms", [])[:5],   # 最多5个表单元素
            text_content=text_content,
            truncated=truncated
        )
    
    def _generate_summary(self, title: str, headings: list, link_count: int, form_count: int) -> str:
        """生成页面摘要"""
        parts = [f"标题: {title}"]
        
        if headings:
            h_text = " | ".join([h["text"] for h in headings[:3]])
            parts.append(f"主要标题: {h_text}")
        
        parts.append(f"链接数: {link_count}, 表单元素: {form_count}")
        
        return "; ".join(parts)
    
    def to_markdown(self, snapshot: PageSnapshot) -> str:
        """将快照转换为 Markdown 格式"""
        lines = [
            f"# {snapshot.title}",
            f"**URL:** {snapshot.url}",
            "",
            f"**摘要:** {snapshot.summary}",
            "",
            "## 页面内容",
            "```",
            snapshot.text_content,
            "```",
        ]
        
        if snapshot.links:
            lines.extend([
                "",
                "## 关键链接",
            ])
            for link in snapshot.links:
                lines.append(f"- [{link['text']}]({link['href']})")
        
        if snapshot.forms:
            lines.extend([
                "",
                "## 交互元素",
            ])
            for form in snapshot.forms:
                desc = form.get("text") or form.get("placeholder") or form.get("name") or form["tag"]
                lines.append(f"- [{form['tag']}] {desc}")
        
        if snapshot.truncated:
            lines.extend([
                "",
                "*注: 页面内容已截断，只显示前 {} 字符*".format(self.max_length)
            ])
        
        return "\n".join(lines)
    
    def to_text(self, snapshot: PageSnapshot) -> str:
        """将快照转换为纯文本格式（更精简）"""
        lines = [
            f"[{snapshot.title}] {snapshot.url}",
            f"摘要: {snapshot.summary}",
            "",
            "内容预览:",
            snapshot.text_content[:500] + "..." if len(snapshot.text_content) > 500 else snapshot.text_content,
        ]
        
        if snapshot.links:
            lines.extend(["", "可用链接:"])
            for link in snapshot.links[:5]:
                lines.append(f"  - {link['text']}: {link['href'][:60]}")
        
        return "\n".join(lines)


# 便捷函数
def capture_snapshot(page, max_length: int = 8000, format: str = "markdown", preheat: bool = True) -> str:
    """
    快速捕获页面快照
    
    Args:
        page: Playwright Page 对象
        max_length: 最大文本长度
        format: 输出格式，"markdown" 或 "text"
        preheat: 是否先滚动预热（触发懒加载），默认开启
    
    Returns:
        str: 格式化的页面快照
    """
    tool = PageSnapshotTool(max_length=max_length)
    snapshot = tool.capture(page, preheat=preheat)
    
    if format == "markdown":
        return tool.to_markdown(snapshot)
    else:
        return tool.to_text(snapshot)
