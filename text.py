import requests
import pytesseract
from PIL import Image
from io import BytesIO
import time
import cv2
import numpy as np

# 设置 tesseract 路径
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# URL 配置
login_url = "http://jwc.swjtu.edu.cn/vatuu/UserLoginAction"
captcha_url = "http://jwc.swjtu.edu.cn/vatuu/GetRandomNumberToJPEG"
course_url = "http://jwc.swjtu.edu.cn/vatuu/CourseAction"

# 用户输入
username = input("请输入学号（username）：")
password = input("请输入密码（password）：")

# 创建会话
session = requests.Session()

# 登录时使用的 headers 模拟浏览器行为
headers = {
    'Referer': 'http://jwc.swjtu.edu.cn/service/login.html',
    'Origin': 'http://jwc.swjtu.edu.cn',
    'User-Agent': 'Mozilla/5.0',
    'DNT': '1',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'X-Requested-With': 'XMLHttpRequest'
}

# 验证码识别函数
def recognize_captcha(img_bytes):
    img = Image.open(BytesIO(img_bytes)).convert('L')
    img_np = np.array(img)
    _, thresh = cv2.threshold(img_np, 127, 255, cv2.THRESH_BINARY)
    thresh = cv2.medianBlur(thresh, 3)
    kernel = np.ones((2, 2), np.uint8)
    processed = cv2.dilate(thresh, kernel, iterations=1)
    img_for_ocr = Image.fromarray(processed)
    text = pytesseract.image_to_string(
        img_for_ocr,
        config='--psm 7 --oem 3 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    )
    return text.strip().replace(" ", "").replace("\n", "")

MAX_ATTEMPTS = 50

# 模拟登录过程
for attempt in range(MAX_ATTEMPTS):
    print(f"\n第 {attempt + 1} 次尝试登录...")

    res = session.get(f"{captcha_url}?t={int(time.time())}", headers=headers)
    ranstring = recognize_captcha(res.content)
    print("识别验证码为：", ranstring)

    if len(ranstring) != 4 or not ranstring.isalnum():
        print("❌ 验证码识别失败，重新尝试...")
        continue

    data = {
        'username': username,
        'password': password,
        'url': 'http://jwc.swjtu.edu.cn/vatuu/UserExitAction&returnUrl',
        'area': '',
        'ranstring': ranstring
    }

    login_res = session.post(login_url, data=data, headers=headers)

    try:
        result = login_res.json()
        login_msg = result.get('loginMsg')
        print("🎉 登录后返回：", login_msg)

        if login_msg and "成功" in login_msg:
            print("✅ 登录成功，准备完成跳转...")

            # 🔧 关键一步：必须访问 UserLoadingAction，完成系统跳转
            loading_url = "http://jwc.swjtu.edu.cn/vatuu/UserLoadingAction"
            loading_data = {
                'url': 'http://jwc.swjtu.edu.cn/vatuu/UserExitAction&returnUrl',
                'returnUrl': '',
                'loginMsg': login_msg
            }
            loading_headers = {
                'User-Agent': headers['User-Agent'],
                'Referer': 'http://jwc.swjtu.edu.cn/service/login.html',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            load_res = session.post(loading_url, data=loading_data, headers=loading_headers)
            print("📥 跳转加载响应状态码：", load_res.status_code)

            # ✅ 再获取课表
            print("📚 跳转完成，开始获取课表...")

            course_headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': headers['User-Agent'],
                'Referer': 'http://jwc.swjtu.edu.cn/vatuu/UserFramework'
            }

            course_data = {
                'setAction': 'userCourseScheduleTable',
                'viewType': 'studentCourseTableWeek',
                'selectTableType': 'ThisTerm',
                'queryType': 'student',
                'weekNo': '7'
            }

            course_res = session.post(course_url, data=course_data, headers=course_headers)

            if "没有操作权限" in course_res.text or "未登陆" in course_res.text:
                print("⚠️ 获取课表失败，可能是未正确跳转或 session 失效")
                continue

            if course_res.status_code == 200:
                print("📄 成功获取课表内容，前 1000 字如下：\n")
                print(course_res.text[:1000])
                with open("课程表.html", "w", encoding="utf-8") as f:
                    f.write(course_res.text)
                print("✅ 已保存为 课程表.html")
            else:
                print("❌ 获取课表失败，返回状态码：", course_res.status_code)

            break

        else:
            print("❌ 登录失败：", login_msg)

    except Exception as e:
        print("❌ 登录异常：", str(e))
        continue

else:
    print("🚫 多次尝试失败，请检查账号、密码或验证码识别逻辑。")
