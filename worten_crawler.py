import scrapy
import os
import datetime
import smtplib
import csv
import json

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from util import parse_int_or_null
from scrapy import signals
from scrapy import Spider

HEADERS = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:48.0) Gecko/20100101 Firefox/48.0'}
WANTED_KW_PATH = 'wanted_keywords.txt'
UNWANTED_KW_PATH = 'unwanted_keywords.txt'
now_format = datetime.datetime.now().strftime("%Y-%m-%d %H_%M")


class WortenSpider(Spider):
    name = "Worten Crawler"
    start_urls = ['https://www.worten.pt/promocoes']

    # create message object instance
    msg = MIMEMultipart()
    # setup the parameters of the message
    password = "price-tracker"
    msg['From'] = "price.tracker.email@gmail.com"
    msg['To'] = "brunocalapez@hotmail.com"
    msg['Subject'] = "PriceTracker " + now_format
    # add in the message body

    # create server
    server = smtplib.SMTP('smtp.gmail.com: 587')
    server.connect('smtp.gmail.com', '587')
    server.starttls()
    # Login Credentials for sending the mail
    server.login(msg['From'], password)
    email_text = ""

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(WortenSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def parse(self, response):
        PRODUCT_SELECTOR = '.w-product'
        for product in response.css(PRODUCT_SELECTOR):
            ID_SELECTOR = '::attr(data-id)'
            NAME_SELECTOR = 'h3 ::text'
            CURR_PRICE_SELECTOR = './/div/a/div/div[2]/div[2]/span[1]/span[2]/text()'
            OLD_PRICE_SELECTOR = './/div/a/div/div[2]/div[2]/span[2]/span[2]/text()'

            item_id = product.css(ID_SELECTOR).extract_first()
            item_name = product.css(NAME_SELECTOR).extract_first()

            if any(map(item_name.lower().__contains__, wanted_keywords)) and not any(map(item_name.lower().__contains__, unwanted_keywords)):

                new_price = parse_int_or_null(product.xpath(CURR_PRICE_SELECTOR).extract_first())
                old_price = parse_int_or_null(product.xpath(OLD_PRICE_SELECTOR).extract_first())

                # Add product if does not exist
                if (item_id, item_name) not in dict_history:
                    dict_history[(item_id, item_name)] = list()

                dict_history[(item_id, item_name)].append(new_price)
                # Calculate discount
                discount = 0
                if old_price is not None and new_price is not None:
                    discount = 1.0 - (float(new_price) / float(old_price))

                # Write to file if is big discount or old/new price does not exist
                if discount >= 0.25 or discount == 0:
                    write_product_to_csv(item_name, old_price, new_price, discount)

                    if discount >= 0.7:
                        self.email_text += str(item_name) + "\t" + str(int(discount * 100)) + "\t" + str(new_price) \
                                      + "\t" + str(old_price) + "\n"

            NEXT_PAGE_SELECTOR = 'a[rel="next"]::attr(href)'
            next_page = response.css(NEXT_PAGE_SELECTOR).extract_first()

            # Crawl next page
            if next_page:
                yield scrapy.Request(
                    response.urljoin(next_page),
                    callback=self.parse,
                    headers=HEADERS
                )

    # Crawler Ended
    def spider_closed(self, spider):
        spider.logger.info('Spider closed: %s', spider.name)
        write_csv_price_history()

        if len(self.email_text) > 0:
            # add in the message body
            self.msg.attach(MIMEText(self.email_text, 'plain'))

            # send the message via the server.
            self.server.sendmail(self.msg['From'], self.msg['To'], self.msg.as_string())
            self.server.quit()
            print("successfully sent email to %s" % (self.msg['To']))
            print(self.email_text)


def write_product_to_csv(item_name, old, new, discount):
    file_path = now_format + ".csv"

    if not os.path.isfile(file_path):
        f = open(file_path, "a", encoding="utf-8")
        f.write("sep=;\n")
        f.write("Item;Discount;Now;Old\n")
        f.close()

    f = open(file_path, "a", encoding="utf-8")
    f.write(str(item_name) + ";" + str(int(discount * 100)) + ";" + str(new) + ";" + str(old) + "\n")
    f.close()


def read_csv_price_history():
    out_dic = dict()

    if not os.path.isfile('price-history.csv'):
        f = open("price-history.csv", "w+")
        f.write('sep=;')
        f.close()

    with open("price-history.csv", encoding="utf8") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=';')

        if os.path.getsize("price-history.csv") > 0:
            # skip the first row
            next(csv_reader)

        # Go through every row (product)
        for row in csv_reader:
            item_id = ""
            item_name = ""

            # Go through every product column
            for idx, col in enumerate(row):
                if idx == 0:  # First column is product id
                    item_id = row[0]
                elif idx == 1:  # Second column is product name
                    item_name = row[1]
                    out_dic[(item_id, item_name)] = list()
                else:  # Remaining columns are the price history
                    out_dic[(item_id, item_name)].append(col)
    csv_file.close()

    return out_dic


def write_csv_price_history():
    with open('price-history.csv', mode='w', encoding="utf-8", newline='') as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=';')
        csv_writer.writerow(['sep=;'])

        for key in dict_history:
            csv_writer.writerow([key[0], key[1]] + dict_history[key])
    csv_file.close()


def get_wanted_keywords(path):
    return open(path).read().lower().splitlines()


def get_unwanted_keywords(path):
    return open(path).read().lower().splitlines()

def remap_keys(mapping):
    return [{'key': k, 'value': v} for k, v in mapping.iteritems()]


wanted_keywords = get_wanted_keywords(WANTED_KW_PATH)
unwanted_keywords = get_unwanted_keywords(UNWANTED_KW_PATH)
# Dictionary of products {(id, name) => [price1, price2, ...]}
dict_history = read_csv_price_history()

