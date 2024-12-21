from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import base64
import json
import matplotlib.pyplot as plt
import requests

def decrypt_aes_ecb(encrypted_data: str) -> str:
    
    key = encrypted_data[:16].encode('utf-8')
    encrypted_data = encrypted_data[16:]
    encrypted_data_bytes = base64.b64decode(encrypted_data)
    
    cipher = AES.new(key, AES.MODE_ECB)
    
    decrypted_data = unpad(cipher.decrypt(encrypted_data_bytes), AES.block_size)

    return decrypted_data.decode('utf-8')

idserial = ""
password = ""
servicehall = ""
all_data = dict()

if __name__ == "__main__":
    # 读入账户信息
    try:
        with open("./config/account.json", "r", encoding='utf-8') as f:
            account = json.load(f)
            idserial = account["idserial"]
            password = account["password"]
            servicehall = account["servicehall"]
    except Exception as e:
        print("账户信息读取失败，请重新输入")
        idserial = input("请输入学号: ")
        password = input("请输入密码: ")
        servicehall = input("请输入服务代码（获取方法详见README.md）: ")
        with open("./config/config.json", "w", encoding='utf-8') as f:
            json.dump({"password": password, "idserial": idserial, "servicehall": servicehall}, f, indent=4)
    
    # 读入配置信息
    try:
        with open("config.json", "r", encoding='utf-8') as f:
            config = json.load(f)
            start_date = config["start_date"]
            end_date = config["end_date"]
            colors = config["colors"][0]
            show_num = config["show_numbers"]
    except Exception as e:
        print("配置信息读取失败，请重新输入")
        start_date = input("请输入查询起始日期（格式：2024-01-01）: ")
        end_date = input("请输入查询结束日期（格式：2024-12-31）: ")
        with open("config.json", "w", encoding='utf-8') as f:
            json.dump({"start_date": "start_date", "end_date": end_date}, f, indent=4)
    
    # 发送请求，得到加密后的字符串
    url = f"https://card.tsinghua.edu.cn/business/querySelfTradeList?pageNumber=0&pageSize=5000&starttime={start_date}&endtime={end_date}&idserial={idserial}&tradetype=-1"
    cookie = {
        "servicehall": servicehall,
    }
    response = requests.post(url, cookies=cookie)

    try: # 解密字符串
        encrypted_string = json.loads(response.text)["data"]
        decrypted_string = decrypt_aes_ecb(encrypted_string)
    except Exception as e:
        print("解密失败，请检查账户信息是否正确，服务代码是否失效")
        exit()

    # 整理数据
    data = json.loads(decrypted_string)
    for item in data["resultData"]["rows"]:
        try:
            if item["mername"] in all_data:
                all_data[item["mername"]] += item["txamt"]
            else:
                all_data[item["mername"]] = item["txamt"]
        except Exception as e:
            pass
    all_data = {k: round(v / 100, 2) for k, v in all_data.items()} # 将分转换为元，并保留两位小数
    sum_data = sum(all_data.values())
    print("统计范围：", start_date, "至", end_date)
    print("消费窗口：", len(all_data), "个")
    print("消费金额：", sum_data, "元")
    
    all_data = dict(sorted(all_data.items(), key=lambda x: x[1], reverse=False))
    plt.rcParams['font.sans-serif'] = ['SimHei']
    
    # 按照大类分组并计算总金额
    category_data = {}
    for key, value in all_data.items():
        category = key.split('_')[0]
        if category in category_data:
            category_data[category] += value
        else:
            category_data[category] = value

    # 准备饼状图的数据
    labels = list(category_data.keys())
    sizes = list(category_data.values())

    total = sum(sizes)  # 总金额
    threshold = 0.02 * total # 2%以下的类别合并到“其它”类别
    other_size = sum(size for size in sizes if size < threshold)
    
    sizes = [size for size in sizes if size >= threshold]
    labels = [label for label in labels if category_data[label] >= threshold]
    sizes, labels = zip(*sorted(zip(sizes, labels), reverse=True))
    sizes = list(sizes)
    labels = list(labels)

    # 如果有“其它”类别，添加到列表中
    if other_size > 0:
        sizes.append(other_size)
        labels.append('其它')

    # 绘制饼状图
    plt.figure(figsize=(8, 8))
    plt.pie(
        sizes, 
        labels=labels, 
        autopct=lambda p: f'{p:.1f}%\n{p*total/100:.1f}元' if p >= 5 and show_num else f'{p:.1f}%',
        startangle=140, 
        colors=colors if colors else None
    )
    plt.title('华清大学校园卡消费情况', fontsize=18, pad=15)
    
    # 在图表底部添加统计信息
    fig = plt.gcf()  # 获取当前图表对象
    
    additonal_text = f'统计范围：{start_date} 至 {end_date}\n窗口数量：{len(all_data)} 个\n'
    if show_num:
        additonal_text += f'总金额：{sum_data} 元\n'
    additonal_text += 'https://github.com/gonglinlu/THU-Annual-Eat-Pie'
    
    fig.text(0.5, 0.02, additonal_text, horizontalalignment='center', fontsize=10)

    plt.tight_layout(pad=3)

    # 保存图片
    plt.savefig('result_pie.png', dpi=300, bbox_inches='tight')
