#!/usr/bin/env python3
"""
MacroChromeMCP WebSocket Server
Python ↔ Browser Extension Bridge
"""

import asyncio
import json
import uuid
import websockets
from typing import Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class BrowserCommand:
    """Represents a command to be sent to the browser"""
    type: str
    data: dict
    id: str = None
    
    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())[:8]
    
    def to_json(self) -> str:
        return json.dumps({
            "id": self.id,
            "type": self.type,
            "data": self.data
        })


class BrowserBridge:
    """
    WebSocket server that bridges Python code with browser extension.
    
    Usage:
        bridge = BrowserBridge()
        await bridge.start()
        
        # Execute JavaScript in browser
        result = await bridge.execute_script("document.title")
        
        # Get page source
        page = await bridge.get_page_source()
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.pending_responses: dict[str, asyncio.Future] = {}
        self.server = None
        self.connected = False
        
    async def start(self):
        """Start the WebSocket server"""
        self.server = await websockets.serve(
            self._handle_connection,
            self.host,
            self.port
        )
        print(f"[Server] WebSocket server started at ws://{self.host}:{self.port}")
        print("[Server] Waiting for browser extension to connect...")
        
    async def stop(self):
        """Stop the server"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        print("[Server] Stopped")
        
    async def _handle_connection(self, websocket):
        """Handle incoming WebSocket connection from browser"""
        print(f"[Server] Browser connected from {websocket.remote_address}")
        self.websocket = websocket
        self.connected = True
        
        try:
            async for message in websocket:
                await self._handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            print("[Server] Browser disconnected")
        finally:
            self.connected = False
            self.websocket = None
            
    async def _handle_message(self, message: str):
        """Handle messages from browser"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            msg_id = data.get("id")
            
            if msg_type == "browser_ready":
                print(f"[Server] Browser ready: {data.get('data', {})}")
                
            elif msg_type == "response":
                # Fulfill pending response
                if msg_id in self.pending_responses:
                    future = self.pending_responses.pop(msg_id)
                    future.set_result(data.get("data"))
                    
            elif msg_type == "error":
                print(f"[Server] Error from browser: {data.get('error')}")
                if msg_id in self.pending_responses:
                    future = self.pending_responses.pop(msg_id)
                    future.set_exception(Exception(data.get("error")))
                    
        except json.JSONDecodeError:
            print(f"[Server] Invalid JSON: {message}")
            
    async def send_command(self, command: BrowserCommand, timeout: float = 30.0) -> Any:
        """Send a command to browser and wait for response"""
        if not self.connected or not self.websocket:
            raise ConnectionError("Browser not connected")
            
        # Create future for response
        future = asyncio.get_event_loop().create_future()
        self.pending_responses[command.id] = future
        
        try:
            # Send command
            await self.websocket.send(command.to_json())
            
            # Wait for response with timeout
            return await asyncio.wait_for(future, timeout=timeout)
            
        except asyncio.TimeoutError:
            self.pending_responses.pop(command.id, None)
            raise TimeoutError(f"Command {command.type} timed out after {timeout}s")
            
    # === High-level API ===
    
    async def execute_script(self, script: str) -> Any:
        """Execute arbitrary JavaScript in the active tab"""
        cmd = BrowserCommand(
            type="execute_script",
            data={"script": script}
        )
        return await self.send_command(cmd)
    
    async def get_page_source(self) -> dict:
        """Get current page URL, title, HTML and text content"""
        cmd = BrowserCommand(type="get_page_source", data={})
        return await self.send_command(cmd)
    
    async def get_element_info(self, selector: str) -> Optional[dict]:
        """Get information about an element by CSS selector"""
        cmd = BrowserCommand(
            type="get_element_info",
            data={"selector": selector}
        )
        return await self.send_command(cmd)
    
    async def click_element(self, selector: str) -> dict:
        """Click an element by CSS selector"""
        cmd = BrowserCommand(
            type="click_element",
            data={"selector": selector}
        )
        return await self.send_command(cmd)
    
    async def type_text(self, selector: str, text: str) -> dict:
        """Type text into an input element"""
        cmd = BrowserCommand(
            type="type_text",
            data={"selector": selector, "text": text}
        )
        return await self.send_command(cmd)
    
    async def find_elements(self, selector: str, limit: int = 10) -> list:
        """Find all elements matching a CSS selector"""
        cmd = BrowserCommand(
            type="find_elements",
            data={"selector": selector, "limit": limit}
        )
        return await self.send_command(cmd)


# === Demo / Test ===

async def demo():
    """Demo script showing how to use the bridge"""
    bridge = BrowserBridge()
    await bridge.start()
    
    print("\n" + "="*60)
    print("Waiting for browser extension to connect...")
    print("Please load the extension in Chrome and open any webpage")
    print("="*60 + "\n")
    
    # Wait for connection
    while not bridge.connected:
        await asyncio.sleep(0.5)
    
    print("\n[Demo] Browser connected! Running tests...\n")
    
    try:
        # Test 1: Execute custom script
        print("[Test 1] Execute custom script...")
        result = await bridge.execute_script("'Hello from Python! Current URL: ' + window.location.href")
        print(f"  Result: {result}")
        
        # Test 2: Get page source
        print("\n[Test 2] Get page source...")
        page = await bridge.get_page_source()
        print(f"  URL: {page.get('url')}")
        print(f"  Title: {page.get('title')}")
        print(f"  HTML length: {len(page.get('html', ''))} chars")
        print(f"  Text length: {len(page.get('text', ''))} chars")
        
        # Test 3: Find elements
        print("\n[Test 3] Find all links...")
        links = await bridge.find_elements("a", limit=5)
        print(f"  Found {len(links)} links:")
        for link in links:
            text = link.get('text', '')[:50] if link.get('text') else '(no text)'
            print(f"    - {link.get('tagName')}: {text}")
        
        # Test 4: Get specific element info
        print("\n[Test 4] Get body element info...")
        body = await bridge.get_element_info("body")
        if body:
            print(f"  Tag: {body.get('tagName')}")
            print(f"  Visible: {body.get('visible')}")
            print(f"  Rect: {body.get('rect')}")
        
        print("\n" + "="*60)
        print("All tests completed successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"\n[Error] {e}")
        
    # Keep server running for more commands
    print("\nServer is running. Press Ctrl+C to stop.")
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        await bridge.stop()


if __name__ == "__main__":
    asyncio.run(demo())
