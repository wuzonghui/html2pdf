# coding=utf-8
import logging
import os
import re
import time
from urllib.parse import urlparse
import pdfkit
import requests
from bs4 import BeautifulSoup

html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <link rel="stylesheet" href="{css1}">
    <link rel="stylesheet" href="{css2}">
    <link rel="stylesheet" href="{css3}">
</head>
<body>
{content}
</body>
</html>

"""


class Crawler(object):
    """
    爬虫基类，所有爬虫都应该继承此类
    """
    name = None

    def __init__(self, name, start_url):
        """
        初始化
        :param name: 保存问的PDF文件名,不需要后缀名
        :param start_url: 爬虫入口URL
        """
        self.name = name
        self.start_url = start_url
        self.domain = '{uri.scheme}://{uri.netloc}'.format(uri=urlparse(self.start_url))

    def crawl(self, url):
        """
        获取response对象
        :return: response
        """
        response = requests.get(url)
        return response

    def parse_menu(self, response):
        """
        解析目录结构,获取所有URL目录列表,由子类实现
        :param response 爬虫返回的response对象
        :return: url 可迭代对象(iterable) 列表,生成器,元组都可以
        """
        raise NotImplementedError

    def parse_body(self, response):
        """
        解析正文,由子类实现
        :param response: 爬虫返回的response对象
        :return: 返回经过处理的html文本
        """
        raise NotImplementedError

    def run(self):
        start = time.time()
        options = {
            'page-size': 'Letter',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
            'custom-header': [
                ('Accept-Encoding', 'gzip,deflate,sdch'),
                ('User-Agent','Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 7Star/2.0.56.2 Safari/537.36'),
                ('Accept','text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'),
            ],
            'outline-depth': 10,
            'quiet':'',
        }
        htmls = []
        for index, url in enumerate(self.parse_menu(self.crawl(self.start_url))):
            html = self.parse_body(self.crawl(url))
            f_name = '.'.join([str(index), 'html'])
            with open(f_name, 'wb') as f:
                f.write(html)
            htmls.append(f_name)
        
        try:
            print('正在生成pdf文件')
            pdfkit.from_file(htmls, self.name + '.pdf', options=options)
        except Exception as e:
            print('转换期间出现错误 {}'.format(e))
        finally:
            for html in htmls:
                os.remove(html)
            total_time = time.time() - start
            print('总共耗时: {:.2f}秒'.format(total_time))


class LiaoxuefengPythonCrawler(Crawler):
    """
    廖雪峰Python3教程
    """

    def parse_menu(self, response):
        """
        解析目录结构,获取所有URL目录列表
        :param response 爬虫返回的response对象
        :return: url生成器
        """
        print('正在获取url')
        soup = BeautifulSoup(response.content, 'lxml')
        menu_tag = soup.find_all(class_='uk-nav-side')[1]
        for li in menu_tag.find_all('li'):
            url = li.a.get('href')
            if not url.startswith('http'):
                url = ''.join([self.domain, url])  # 补全为全路径
            yield url

    def parse_body(self, response):
        """
        解析正文
        :param response: 爬虫返回的response对象
        :return: 返回处理后的html文本
        """
        try:
            soup = BeautifulSoup(response.content, 'lxml')
            body = soup.find_all(class_='x-wiki-content')[0]
            css1 = 'http://www.liaoxuefeng.com' + str(soup.find_all('link')[1].get('href'))
            css2 = 'http://www.liaoxuefeng.com' + str(soup.find_all('link')[2].get('href'))
            css3 = 'http://www.liaoxuefeng.com' + str(soup.find_all('link')[3].get('href'))
            
            #删除无用的文档树
            while body.video != None:
                body.video.extract()
            # 加入标题, 居中显示
            title = soup.find('h4').get_text()
            center_tag = soup.new_tag('center')
            title_tag = soup.new_tag('h1')
            title_tag.string = title
            center_tag.insert(1, title_tag)
            body.insert(1, center_tag)
            
            print('正在解析 {title}'.format(title=title))
            html = str(body)
            # body中的img标签的src相对路径的改成绝对路径
            pattern = "(<img .*?src=\")(.*?)(\")"

            def func(m):
                if not m.group(2).startswith('http'):
                    rtn = ''.join([m.group(1), self.domain, m.group(2), m.group(3)])
                    return rtn
                else:
                    return ''.join([m.group(1), m.group(2), m.group(3)])

            html = re.compile(pattern).sub(func, html)
            html = html_template.format(content=html,css1=css1,css2=css2,css3=css3)
            html = html.encode('utf-8')
            return html
        except Exception:
            logging.error('解析错误', exc_info=True)


if __name__ == '__main__':
    start_url = 'http://www.liaoxuefeng.com/wiki/0013739516305929606dd18361248578c67b8067c8c017b000'
    crawler = LiaoxuefengPythonCrawler('lxf-git', start_url)
    crawler.run()
