import os
import subprocess
import sys
import time
import signal
import atexit

def start_servers():
    """Start both the MCP server and the ADK web test interface."""
    print("Starting MCP server and ADK web test interface...")
    
    # Start the MCP server
    mcp_process = subprocess.Popen(
        [sys.executable, "multi_tool_agent/mcp_server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for the MCP server to start
    time.sleep(2)
    
    # Start the ADK web test interface
    adk_process = subprocess.Popen(
        [sys.executable, "multi_tool_agent/adk_web_test.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Register cleanup function
    def cleanup():
        print("\nShutting down servers...")
        mcp_process.terminate()
        adk_process.terminate()
        mcp_process.wait()
        adk_process.wait()
        print("Servers shut down successfully.")
    
    atexit.register(cleanup)
    
    # Handle Ctrl+C
    def signal_handler(sig, frame):
        print("\nReceived Ctrl+C, shutting down...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    print("MCP server started on http://localhost:8080")
    print("ADK web test interface started on http://localhost:5000")
    print("Press Ctrl+C to shut down both servers")
    
    # Keep the script running
    try:
        while True:
            time.sleep(1)
            
            # Check if processes are still running
            if mcp_process.poll() is not None:
                print("MCP server has stopped unexpectedly")
                break
            
            if adk_process.poll() is not None:
                print("ADK web test interface has stopped unexpectedly")
                break
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    start_servers() 