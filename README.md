# MrRobot-recon
Lightweight recon and enumeration orchestrator: nmap, gobuster, FTP, SMB.
Purpose
-------
A small Python3 script that automates basic reconnaissance and lightweight exploitation steps in lab environments. Designed as a compact, easy-to-iterate learning tool.

What it does (high-level)
-------------------------
1. Runs an nmap service scan and saves results to `nmap_result.txt`.
2. If HTTP (80) or HTTPS (443) is detected, runs Gobuster and saves results to `gobuster_http.txt` and/or `gobuster_https.txt`.
3. If FTP (21) is detected, attempts anonymous FTP login:
   - If login succeeds, lists files and writes them to `ftp_files.txt`.
   - If a `reverse_shell_template.php` file exists and a web service is present, prompts for a listener IP, substitutes it into the template, creates `reverse_shell.php`, and attempts to upload it to the FTP server.
   - If upload succeeds and `gnome-terminal` + `nc` are available, spawns a terminal running `nc -lvnp 4444`. Otherwise prints the listener command to run manually.
   - Attempts an HTTP GET to trigger the uploaded PHP file.
4. If SMB ports (139/445) are detected and `smbclient` is present, runs an anonymous SMB share listing and saves output to `smb_shares_<ip>.txt`.

How it works (step-by-step)
---------------------------
1. Ask the user for the target IP and validate it.
2. Run:
   `nmap -sV -Pn -oN nmap_result.txt <target-ip>`
   and save the text output.
3. Parse `nmap_result.txt` (simple text checks) to detect services: HTTP, HTTPS, FTP, SMB.
4. If HTTP/HTTPS detected and `gobuster` exists, run Gobuster with a wordlist and save output files.
5. If FTP detected:
   - Connect with `ftplib` and attempt anonymous login.
   - Use `nlst()` (or fallback) to list files and write `ftp_files.txt`.
   - If `reverse_shell_template.php` exists and HTTP(S) detected, prompt for listener IP, produce `reverse_shell.php`, upload with `STOR`, and report result.
   - Optionally spawn a terminal with a netcat listener if available.
   - Trigger the uploaded file via HTTP GET to attempt a reverse shell connection.
6. If SMB detected and `smbclient` is available, run:
   `smbclient -L <ip> -N` and save the output.

Files produced
--------------
- `nmap_result.txt`           — nmap output (text)
- `gobuster_http.txt`         — gobuster output for HTTP (if run)
- `gobuster_https.txt`        — gobuster output for HTTPS (if run)
- `ftp_files.txt`             — file/directory listing from FTP (if anon login succeeds)
- `reverse_shell.php`         — generated from template (created before upload)
- `smb_shares_<ip>.txt`       — smbclient output (if run)
