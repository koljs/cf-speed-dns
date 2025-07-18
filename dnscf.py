import requests
import traceback
import time
import os
import json

# API 密钥
CF_API_TOKEN    =   os.environ["CF_API_TOKEN"]
CF_ZONE_ID      =   os.environ["CF_ZONE_ID"]
CF_DNS_NAME     =   os.environ["CF_DNS_NAME"]

# pushplus_token
PUSHPLUS_TOKEN  =   os.environ["PUSHPLUS_TOKEN"]

headers = {
    'Authorization': f'Bearer {CF_API_TOKEN}',
    'Content-Type': 'application/json'
}

def get_cf_speed_test_ip(timeout=10, max_retries=5):
    for attempt in range(max_retries):
        try:
            # 发送 GET 请求，设置超时
            response = requests.get('https://ip.164746.xyz/ipTop.html', timeout=timeout)
            # 检查响应状态码
            if response.status_code == 200:
                return response.text
        except Exception as e:
            traceback.print_exc()
            print(f"get_cf_speed_test_ip Request failed (attempt {attempt + 1}/{max_retries}): {e}")
            time.sleep(2)  # 重试前等待2秒
    # 如果所有尝试都失败，返回 None
    return None

# 获取 DNS 记录
def get_dns_records(name):
    def_info = []
    url = f'https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/dns_records'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        records = response.json()['result']
        for record in records:
            if record['name'] == name:
                def_info.append(record['id'])
        return def_info
    else:
        print('Error fetching DNS records:', response.text)
        return []

# 更新 DNS 记录
def update_dns_record(record_id, name, cf_ip):
    url = f'https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/dns_records/{record_id}'
    data = {
        'type': 'A',
        'name': name,
        'content': cf_ip,
        'ttl': 1,  # 添加TTL设置（1秒表示自动）
        'proxied': False  # 添加代理设置（根据需要修改）
    }

    response = requests.put(url, headers=headers, json=data)

    if response.status_code == 200:
        print(f"cf_dns_change success: ---- Time: {time.strftime('%Y-%m-%d %H:%M:%S')} ---- ip: {cf_ip}")
        return f"ip: {cf_ip} 解析 {name} 成功"
    else:
        print(f"cf_dns_change ERROR: ---- Time: {time.strftime('%Y-%m-%d %H:%M:%S')} ---- Response: {response.text}")
        return f"ip: {cf_ip} 解析 {name} 失败 (状态码: {response.status_code})"

# 消息推送
def push_plus(content):
    url = 'http://www.pushplus.plus/send'
    data = {
        "token": PUSHPLUS_TOKEN,
        "title": "IP优选DNSCF推送",
        "content": content,
        "template": "markdown",
        "channel": "wechat"
    }
    try:
        body = json.dumps(data).encode(encoding='utf-8')
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, data=body, headers=headers)
        if response.status_code != 200:
            print(f"PushPlus 推送失败: {response.text}")
    except Exception as e:
        print(f"PushPlus 推送异常: {e}")

# 主函数
def main():
    # 获取最新优选IP
    ip_addresses_str = get_cf_speed_test_ip()
    
    # 输入验证
    if not ip_addresses_str:
        error_msg = "获取IP地址失败，可能测速网站无法访问"
        print(error_msg)
        push_plus(error_msg)
        return
    
    # 分割IP地址并过滤空值
    ip_addresses = [ip.strip() for ip in ip_addresses_str.split(',') if ip.strip()]
    
    if not ip_addresses:
        error_msg = "解析后没有有效的IP地址"
        print(error_msg)
        push_plus(error_msg)
        return
    
    # 获取DNS记录
    dns_records = get_dns_records(CF_DNS_NAME)
    
    if not dns_records:
        error_msg = f"未找到域名 {CF_DNS_NAME} 的DNS记录，请检查域名配置"
        print(error_msg)
        push_plus(error_msg)
        return
    
    push_plus_content = []
    
    # 确保只处理存在的DNS记录数量
    max_updates = min(len(dns_records), len(ip_addresses))
    
    # 遍历 IP 地址列表和DNS记录
    for i in range(max_updates):
        record_id = dns_records[i]
        ip_address = ip_addresses[i]
        
        # 执行 DNS 变更
        dns_result = update_dns_record(record_id, CF_DNS_NAME, ip_address)
        push_plus_content.append(dns_result)
    
    # 报告更新情况
    update_summary = f"\n\n更新摘要：成功更新 {max_updates} 条记录"
    if len(ip_addresses) > len(dns_records):
        update_summary += f"，忽略了 {len(ip_addresses) - len(dns_records)} 个多余IP地址"
    elif len(ip_addresses) < len(dns_records):
        update_summary += f"，剩余 {len(dns_records) - len(ip_addresses)} 条记录未更新"
    
    push_plus_content.append(update_summary)
    push_plus('\n'.join(push_plus_content))

if __name__ == '__main__':
    main()
