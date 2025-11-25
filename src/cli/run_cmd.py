def run_cmd(command: str):
    import subprocess
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout, result.stderr
