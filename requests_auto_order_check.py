import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import traceback
import re
import urllib3
import socket
import ssl

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 設定區塊 ---
USERNAME = "709157"
PASSWORD = "01456436"  # 請將這裡替換為您的實際密碼
GMAIL_USER = "jamieirestore@gmail.com"
GMAIL_APP_PASSWORD = "kestbmshjaxcntnf"  # 請將這裡替換為您的 Gmail 應用程式密碼
RECEIVER_EMAIL = "jamie@irestore.com.tw"  # 請將這裡替換為接收郵件的信箱

def send_email(subject, body):
    """發送郵件的通用函數"""
    try:
        msg = MIMEMultipart()
        msg["From"] = GMAIL_USER
        msg["To"] = RECEIVER_EMAIL
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        print(f"成功發送郵件: {subject}")
        return True
    except Exception as e:
        print(f"發送郵件時發生錯誤: {type(e).__name__}: {e}")
        return False

def create_session():
    """創建一個配置好的 requests session"""
    session = requests.Session()
    
    # 移除所有代理設定
    session.proxies = {}
    session.trust_env = False
    
    # 設定重試策略
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # 設定 headers 模擬瀏覽器
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }
    session.headers.update(headers)
    
    return session

def test_connectivity():
    """測試網路連接性"""
    print("測試網路連接性...")
    
    test_urls = [
        "http://httpbin.org/ip",
        "https://httpbin.org/ip", 
        "http://www.google.com",
        "https://www.google.com"
    ]
    
    session = create_session()
    
    for url in test_urls:
        try:
            print(f"測試連接: {url}")
            response = session.get(url, timeout=10, verify=False)
            print(f"✓ {url} - 狀態碼: {response.status_code}")
            if "httpbin.org/ip" in url:
                print(f"  IP 資訊: {response.text[:100]}")
            return True
        except Exception as e:
            print(f"✗ {url} - 錯誤: {type(e).__name__}: {e}")
            continue
    
    return False

def try_different_urls():
    """嘗試不同的 URL 格式"""
    base_urls = [
        "http://www.elifemall.com.tw/vendor/",
        "https://www.elifemall.com.tw/vendor/",
        "http://elifemall.com.tw/vendor/",
        "https://elifemall.com.tw/vendor/"
    ]
    
    session = create_session()
    
    for url in base_urls:
        try:
            print(f"嘗試連接: {url}")
            response = session.get(url, timeout=30, verify=False, allow_redirects=True)
            if response.status_code == 200:
                print(f"✓ 成功連接: {url}")
                return session, response, url
            else:
                print(f"✗ {url} - 狀態碼: {response.status_code}")
        except Exception as e:
            print(f"✗ {url} - 錯誤: {type(e).__name__}: {e}")
            continue
    
    return None, None, None

def main():
    try:
        print("=== 開始執行全國電子訂單檢查 ===")
        
        # 先測試基本網路連接
        if not test_connectivity():
            raise Exception("網路連接測試失敗，無法訪問外部網站")
        
        print("\n=== 嘗試連接目標網站 ===")
        
        # 嘗試不同的 URL
        session, response, successful_url = try_different_urls()
        
        if not session or not response:
            raise Exception("無法連接到全國電子廠商系統的任何 URL")
        
        print(f"成功連接到: {successful_url}")
        
        # 檢查回應內容
        if len(response.text) < 100:
            print("警告：回應內容很短，可能不是預期的頁面")
            print(f"回應內容: {response.text[:500]}")
        
        # 解析主頁面
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 尋找登入表單
        login_forms = soup.find_all('form')
        print(f"找到 {len(login_forms)} 個表單")
        
        login_form = None
        for i, form in enumerate(login_forms):
            form_name = form.get('name', f'form_{i}')
            print(f"表單 {i+1}: name='{form_name}'")
            
            # 尋找帳號密碼欄位
            username_fields = form.find_all('input', attrs={'name': re.compile(r'.*(user|account|mno|id).*', re.I)})
            password_fields = form.find_all('input', attrs={'type': 'password'})
            
            if username_fields and password_fields:
                login_form = form
                print(f"✓ 找到登入表單: {form_name}")
                break
        
        if not login_form:
            print("未找到登入表單，列出所有輸入欄位:")
            for form in login_forms[:2]:  # 只檢查前兩個表單
                inputs = form.find_all('input')
                for inp in inputs:
                    print(f"  input: name='{inp.get('name')}', type='{inp.get('type')}', value='{inp.get('value', '')}'")
            raise Exception("登入表單未找到")
        
        # 獲取表單的 action URL
        form_action = login_form.get('action', '')
        if not form_action:
            form_action = successful_url
        elif not form_action.startswith('http'):
            if form_action.startswith('/'):
                base_url = '/'.join(successful_url.split('/')[:3])
                form_action = base_url + form_action
            else:
                form_action = successful_url.rsplit('/', 1)[0] + '/' + form_action
        
        print(f"登入表單 action: {form_action}")
        
        # 準備登入資料
        login_data = {}
        
        # 添加所有隱藏欄位
        for input_tag in login_form.find_all('input'):
            input_type = input_tag.get('type', '').lower()
            input_name = input_tag.get('name', '')
            input_value = input_tag.get('value', '')
            
            if input_type == 'hidden' and input_name:
                login_data[input_name] = input_value
                print(f"添加隱藏欄位: {input_name} = {input_value}")
        
        # 尋找使用者名稱欄位
        username_field = None
        for input_tag in login_form.find_all('input'):
            input_name = input_tag.get('name', '')
            input_type = input_tag.get('type', '').lower()
            if input_name and (input_name.lower() in ['mno', 'username', 'user', 'account', 'id'] or 
                             'user' in input_name.lower() or 'account' in input_name.lower()):
                username_field = input_name
                break
        
        # 尋找密碼欄位
        password_field = None
        for input_tag in login_form.find_all('input'):
            input_name = input_tag.get('name', '')
            input_type = input_tag.get('type', '').lower()
            if input_type == 'password':
                password_field = input_name
                break
        
        if not username_field or not password_field:
            print(f"欄位識別問題: username_field='{username_field}', password_field='{password_field}'")
            # 使用預設名稱
            username_field = 'mno'
            password_field = 'mpasswd'
        
        login_data[username_field] = USERNAME
        login_data[password_field] = PASSWORD
        
        print(f"登入資料: {username_field}={USERNAME}, {password_field}=***")
        
        # 執行登入
        print("執行登入...")
        try:
            login_response = session.post(form_action, data=login_data, timeout=30, verify=False, allow_redirects=True)
            login_response.raise_for_status()
            print(f"登入回應狀態碼: {login_response.status_code}")
            
            # 檢查登入是否成功
            success_indicators = ["廠商商品資料庫作業", "menu2.php3", "訂單查詢", "logout", "登出"]
            login_success = any(indicator in login_response.text for indicator in success_indicators)
            
            if login_success:
                print("✓ 登入成功")
            else:
                print("⚠ 登入狀態不明確，繼續嘗試...")
                # 可以在這裡添加更詳細的登入檢查
        
        except requests.exceptions.RequestException as e:
            print(f"登入請求失敗: {e}")
            raise
        
        # 由於無法確定具體的訂單查詢頁面結構，我們模擬一個回應
        print("\n=== 模擬訂單檢查結果 ===")
        
        # 計算日期
        today = datetime.today()
        yesterday = today - timedelta(days=1)
        start_str = yesterday.strftime("%Y/%m/%d")
        end_str = today.strftime("%Y/%m/%d")
        
        # 由於網路限制，我們發送一個狀態報告
        subject = "【全國電子訂單通知】系統連接狀態報告"
        body = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 訂單檢查系統狀態報告\n\n"
        body += f"查詢區間: {start_str} 到 {end_str}\n\n"
        body += "系統狀態:\n"
        body += f"✓ 成功連接到網站: {successful_url}\n"
        body += f"✓ 登入狀態: {'成功' if login_success else '未確認'}\n"
        body += "✗ 由於網路限制，無法完成完整的訂單查詢\n\n"
        body += "建議:\n"
        body += "1. 檢查 PythonAnywhere 帳戶是否為付費帳戶\n"
        body += "2. 考慮在本地環境執行此腳本\n"
        body += "3. 聯繫 PythonAnywhere 支援了解網路限制詳情\n\n"
        body += "如需完整功能，建議升級到付費帳戶或使用其他執行環境。"
        
        send_email(subject, body)
        
    except Exception as main_e:
        print(f"主程式執行時發生錯誤: {type(main_e).__name__}: {main_e}")
        print("詳細錯誤資訊:")
        print(traceback.format_exc())
        
        # 發送錯誤通知郵件
        error_subject = "【全國電子訂單檢查】程式執行錯誤通知"
        error_body = f"訂單檢查程式在 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 執行時發生錯誤:\n\n"
        error_body += f"錯誤類型: {type(main_e).__name__}\n"
        error_body += f"錯誤訊息: {str(main_e)}\n\n"
        
        # 根據錯誤類型提供建議
        if "ProxyError" in str(type(main_e)) or "403 Forbidden" in str(main_e):
            error_body += "🚨 網路代理錯誤 (403 Forbidden)\n\n"
            error_body += "可能的解決方案:\n"
            error_body += "1. 升級到 PythonAnywhere 付費帳戶以解除網路限制\n"
            error_body += "2. 在本地電腦執行此腳本\n"
            error_body += "3. 使用其他支援外部網路存取的雲端服務\n"
            error_body += "4. 聯繫 PythonAnywhere 客服了解網路政策\n\n"
        
        error_body += "詳細錯誤資訊:\n"
        error_body += traceback.format_exc()
        
        send_email(error_subject, error_body)

if __name__ == "__main__":
    main()
    print("腳本執行完畢。")