# queuectl/executor.py
import subprocess

def execute_job_command(command: str):
    """
    Executes a shell command and returns its exit code.
    
    Returns 0 for success, non-zero for failure.
    """
    try:
        # We use shell=True to interpret the command as a shell string
        # (e.g., "echo 'Hello World'")
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=3600 # 1 hour timeout, can be configured later
        )
        
        if result.returncode != 0:
            print(f"Command failed with exit code {result.returncode}")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            
        return result.returncode
        
    except subprocess.TimeoutExpired:
        print(f"Command '{command}' timed out.")
        return -1 # Use a custom code for timeout
    except Exception as e:
        print(f"Error executing command '{command}': {e}")
        return -1 # Indicate failure