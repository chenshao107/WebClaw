"""
浏览器启动参数、User-Agent、本地调试端口配置
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import os


@dataclass
class BrowserConfig:
    """
    浏览器配置类
    
    包含浏览器启动参数、User-Agent、调试端口等配置
    """
    
    # 基本配置
    headless: bool = False
    slow_mo: int = 0  # 操作延迟（毫秒）
    
    # 视口配置
    viewport_width: int = 1920
    viewport_height: int = 1080
    
    # 远程调试配置
    debug_port: Optional[int] = None  # 如 9222
    
    # User-Agent
    user_agent: Optional[str] = None
    
    # 启动参数
    args: List[str] = field(default_factory=list)
    
    # 上下文配置
    locale: str = "zh-CN"
    timezone_id: str = "Asia/Shanghai"
    
    # 其他选项
    downloads_path: Optional[str] = None
    accept_downloads: bool = True
    
    def __post_init__(self):
        """初始化后的处理"""
        # 设置默认 User-Agent
        if not self.user_agent:
            self.user_agent = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        
        # 设置默认启动参数
        if not self.args:
            self.args = [
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-site-isolation-trials",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-gpu",
                "--disable-webgl",
                "--disable-software-rasterizer",
            ]
    
    def to_launch_options(self) -> Dict[str, Any]:
        """
        转换为 Playwright launch 选项
        
        Returns:
            launch 选项字典
        """
        options = {
            "headless": self.headless,
            "args": self.args,
        }
        
        if self.slow_mo > 0:
            options["slow_mo"] = self.slow_mo
            
        return options
    
    def to_context_options(self) -> Dict[str, Any]:
        """
        转换为 Playwright context 选项
        
        Returns:
            context 选项字典
        """
        options = {
            "viewport": {
                "width": self.viewport_width,
                "height": self.viewport_height
            },
            "locale": self.locale,
            "timezone_id": self.timezone_id,
            "user_agent": self.user_agent,
            "accept_downloads": self.accept_downloads,
        }
        
        if self.downloads_path:
            options["downloads_path"] = self.downloads_path
            
        return options
    
    @classmethod
    def from_env(cls) -> "BrowserConfig":
        """
        从环境变量加载配置
        
        Returns:
            BrowserConfig 实例
        """
        return cls(
            headless=os.getenv("BROWSER_HEADLESS", "false").lower() == "true",
            debug_port=int(os.getenv("BROWSER_DEBUG_PORT", "0")) or None,
            viewport_width=int(os.getenv("BROWSER_VIEWPORT_WIDTH", "1920")),
            viewport_height=int(os.getenv("BROWSER_VIEWPORT_HEIGHT", "1080")),
            slow_mo=int(os.getenv("BROWSER_SLOW_MO", "0")),
        )


def get_default_config(headless: bool = False, debug_port: Optional[int] = None) -> BrowserConfig:
    """
    获取默认浏览器配置
    
    Args:
        headless: 是否无头模式
        debug_port: 调试端口
        
    Returns:
        BrowserConfig 实例
    """
    return BrowserConfig(
        headless=headless,
        debug_port=debug_port
    )


def get_stealth_config() -> BrowserConfig:
    """
    获取防检测浏览器配置
    
    用于绕过一些网站的基本 bot 检测
    
    Returns:
        BrowserConfig 实例
    """
    return BrowserConfig(
        headless=False,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-site-isolation-trials",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-infobars",
            "--window-size=1920,1080",
            "--window-position=0,0",
            "--ignore-certificate-errors",
            "--ignore-certificate-errors-spki-list",
            "--disable-accelerated-2d-canvas",
            "--disable-gl-drawing-for-tests",
            "--disable-background-networking",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-breakpad",
            "--disable-component-extensions-with-background-pages",
            "--disable-default-apps",
            "--disable-extensions",
            "--disable-features=TranslateUI",
            "--disable-hang-monitor",
            "--disable-ipc-flooding-protection",
            "--disable-popup-blocking",
            "--disable-prompt-on-repost",
            "--disable-renderer-backgrounding",
            "--force-color-profile=srgb",
            "--metrics-recording-only",
            "--no-first-run",
            "--safebrowsing-disable-auto-update",
            "--enable-automation",
            "--password-store=basic",
            "--use-mock-keychain",
        ],
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
        )
    )
