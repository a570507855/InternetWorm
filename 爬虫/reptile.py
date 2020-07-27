import requests
import re
import tldextract
import cchardet
import os
import random
import time
import redis
import mysql.connector
import cchardet
import threading


# 根据页面链接，获取该页面中的所有href
def get_href_link(href):
    try:
        _requests = requests.get(href)
        _protocol = re.match('(.*?):', href).group(1)
        html = _requests.text
        hLink = re.findall(r'href=[\'"]+(.*?)[\'"\s]', html)
        tld = tldextract.extract(href)
        subdomain = tld.subdomain
        domain = tld.domain
        suffix = tld.suffix
        host = (subdomain if subdomain != "" else "") + ("." + domain if domain != "" else "") + (
            "." + suffix if suffix != "" else "")
        href_links = []
        for link in hLink:
            if re.search('(.*).(css|js|png)', link) or not link.startswith('http') and not link.startswith('/'):
                continue
            if link.startswith('//'):
                href_links.append(_protocol + ':' + link)
            elif link.startswith('/'):
                href_links.append(_protocol + '://' + host + link)
            else:
                href_links.append(link)
        return href_links
    except Exception as e:
        print("触发异常的链接：" + str(href))
        print("异常内容：" + str(e))
        return []


# 根据页面链接，获取该页面中的所有src
def get_src_link(href):
    _requests = requests.get(href)
    _protocol = re.match('(.*?):', href).group(1)
    html = _requests.text
    tld = tldextract.extract(href)
    subdomain = tld.subdomain
    domain = tld.domain
    suffix = tld.suffix
    host = (subdomain if subdomain != "" else "") + ("." + domain if domain != "" else "") + (
        "." + suffix if suffix != "" else "")
    sLink = re.findall(r'src=[\'"]+(.*?)[\'"\s]', html)
    src_links = []
    for link in sLink:
        if re.search('(.*).(css|js)', link) or not link.startswith('http') and not link.startswith('/'):
            continue
        if link.startswith('//'):
            src_links.append(_protocol + ':' + link)
        elif link.startswith('/'):
            src_links.append(_protocol + '://' + host + link)
        else:
            src_links.append(link)
    return src_links


# 根据页面链接，获取该链接的信息
def get_link_info(link):
    status_code = ''  # 响应状态码
    cookie = ''  # cookie
    encoding = ''  # 文本编码
    content_type = ''  # 类型
    title = ''  # 标题
    description = ''  # 网页描述
    keywords = ''  # 关键字
    content = ''  # 网页内容
    url = link  # 链接
    protocol = re.match('(.*?):', link).group(1)
    tld = tldextract.extract(link)  # 获取链接的子域，域，后缀
    subdomain = tld.subdomain  # 子域
    domain = tld.domain  # 域
    suffix = tld.suffix  # 后缀
    host = (subdomain if subdomain != "" else "") + ("." + domain if domain != "" else "") + (
        "." + suffix if suffix != "" else "")  # 获取主机地址
    try:
        r = requests.get(link)  # 发起请求
        status_code = r.status_code
        content_type = r.headers['Content-Type']
        cookie = r.cookies
        encoding = str(cchardet.detect(r.content)["encoding"])
        if encoding.find("UTF-8") != -1:
            content = r.content.decode("utf-8")
        else:
            content = r.content.decode("gbk")
        titleGroup = re.search(r'<title>(.*)</title>', content, re.I)
        keywordsGroup = re.search(r'<meta name="keywords" content="(.*?)" >?', content, re.I)
        descriptionGroup = re.search(r'<meta name="description" content="(.*?)" >?', content, re.I)
        if titleGroup is not None:
            title = titleGroup.group(1)
        if keywordsGroup is not None:
            keywords = keywordsGroup.group(1)
        if descriptionGroup is not None:
            description = descriptionGroup.group(1)
    except requests.exceptions.Timeout:
        status_code = 408
        print("触发异常的连接：" + str(link))
        print("等待超时！！！")
    except requests.ConnectionError:
        status_code = 408
        print("触发异常的连接：" + str(link))
        print("连接异常")
    except requests.HTTPError:
        status_code = r.status_code
        print("触发异常的连接：" + str(link))
        print("错误请求，响应状态码：" + str(r.status_code))
    except Exception as e:
        print("触发异常的连接：" + str(link))
        print("异常内容：" + str(e))
    finally:
        webURL_dict = {
            "url": url,
            "host": host,
            "protocol": protocol,
            "subdomain": subdomain,
            "domain": domain,
            "suffix": suffix,
            "status_code": status_code,
            "cookie": cookie,
            "encoding": encoding,
            "type": content_type,
            "title": title.replace('"', '\''),
            "description": description.replace('"', '\''),
            "keywords": keywords.replace('"', '\''),
            "content": content.replace('"', '\'')
        }
        return webURL_dict


# 根据图片链接下载并保存
def get_image(src_links):
    imgFormat = {'webp', 'bmp', 'pcx', 'tif', 'gif', 'jpeg', 'jpg', 'tga', 'exif', 'fpx', 'svg', 'psd', 'cdr',
                 'pcd', 'dxf', 'ufo', 'eps', 'ai', 'png', 'hdri', 'raw', 'wmf', 'flic', 'emf', 'ico'}
    index = 0
    for link in src_links:
        index += 1
        suffix = link.split('.')[-1]
        fileName = time.strftime("%Y%m%d%H%M%S") + str(index).zfill(4)
        if suffix in imgFormat:
            # 判断是否存在文件夹，若不存在则创建
            if not os.path.exists('../img/' + suffix):
                os.mkdir('../img/' + suffix)
            imageR = requests.get(link)
            # 打开文件并写入图片的二进制数据
            with open('../img/' + suffix + '/' + fileName + '.' + suffix, 'wb') as file:
                file.write(imageR.content)
                file.flush()
            file.close()


class reptile:
    __redis = ''  # 操作redis键值数据库实例
    __mysql = ''  # 操作mysql关系数据库实例
    __mysql_cursor = ''  # 操作mysql游标

    # 构造函数
    def __init__(self):
        redis_pool = redis.ConnectionPool(host='127.0.0.1', port=6379, password='disueb11', db=0)  # 建立连接池
        self.__mysql = mysql.connector.connect(
            host="localhost",  # 数据库主机地址
            user="root",  # 数据库用户名
            passwd="disueb11",  # 数据库密码
            auth_plugin='mysql_native_password',
            database='mybatis'
        )
        self.__mysql_cursor = self.__mysql.cursor()
        self.__redis = redis.Redis(connection_pool=redis_pool)  # 连接redis

    # 祈构函数
    def __del__(self):
        self.__mysql.close

    # mysql新增（通用）
    def mysql_insert(self, _dict, tableName):
        if isinstance(_dict, dict):
            keys = ''
            values = ''
            for key, value in _dict.items():
                keys += key + ','
                values += '"' + str(value) + '",'
            sql = "INSERT INTO " + tableName + " (" + keys[:-1] + ") VALUES (" + values[:-1] + ")"
            self.__mysql_cursor.execute(sql)
            self.__mysql.commit()

    # redis新增
    def redis_set(self, key, value):
        if not self.__redis.exists(key):
            self.__redis.set(key, value)
            return True
        return False


reptile = reptile()
slinks = get_src_link("https://www.ivsky.com")
hlinks = get_href_link("https://www.ivsky.com")

_list = []
try:
    for link in hlinks:
        print(link)
        while link.endswith('/'):
            link = link[:-1]
        _list += get_href_link(link)
        if reptile.redis_set(link, 1):
            linkInfo = get_link_info(link)
            reptile.mysql_insert(linkInfo, "web_url")
    for link in _list:
        print(link)
        while link.endswith('/'):
            link = link[:-1]
        if reptile.redis_set(link, 1):
            linkInfo = get_link_info(link)
            reptile.mysql_insert(linkInfo, "web_url")
except Exception as e:
    print("触发异常的链接：" + str(link))
    print("异常内容：" + str(e))





