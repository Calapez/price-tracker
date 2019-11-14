import scrapy
import os
import datetime

from util import parse_int_or_null

WANTED_KW_PATH = 'wanted_keywords.txt'
UNWANTED_KW_PATH = 'unwanted_keywords.txt'


class WortenSpider(scrapy.Spider):
    name = "Worten Crawler"
    start_urls = ['https://www.worten.pt/promocoes']

    def parse(self, response):
        PRODUCT_SELECTOR = '.w-product'
        for product in response.css(PRODUCT_SELECTOR):
            NAME_SELECTOR = 'h3 ::text'
            CURR_PRICE_SELECTOR = './/div/a/div/div[2]/div[2]/span[1]/span[2]/text()'
            OLD_PRICE_SELECTOR = './/div/a/div/div[2]/div[2]/span[2]/span[2]/text()'

            item_name = product.css(NAME_SELECTOR).extract_first()

            if any(map(item_name.lower().__contains__, wanted_keywords)) and not any(map(item_name.lower().__contains__, unwanted_keywords)):
                new_price = parse_int_or_null(product.xpath(CURR_PRICE_SELECTOR).extract_first())
                old_price = parse_int_or_null(product.xpath(OLD_PRICE_SELECTOR).extract_first())

                discount = 0
                if old_price is not None and new_price is not None:
                    discount = 1.0 - (float(new_price) / float(old_price))

                # Big discount or old/new price is non-existing
                if discount >= 0.25 or discount == 0:
                    write_product(item_name, old_price, new_price, discount)

            NEXT_PAGE_SELECTOR = 'a[rel="next"]::attr(href)'
            next_page = response.css(NEXT_PAGE_SELECTOR).extract_first()
            if next_page:
                yield scrapy.Request(
                    response.urljoin(next_page),
                    callback=self.parse
                )


def write_product(item_name, old, new, discount):
    now_format = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    file_path = now_format + ".csv"

    if not os.path.isfile(file_path):
        f = open(file_path, "a")
        f.write("sep=;\n")
        f.write("Item;Discount;Now;Old\n")
        f.close()

    f = open(file_path, "a")
    f.write(str(item_name) + ";" + str(int(discount * 100)) + ";" + str(new) + ";" + str(old) + "\n")
    f.close()


def get_wanted_keywords(path):
    return open(path).read().lower().splitlines()


def get_unwanted_keywords(path):
    return open(path).read().lower().splitlines()


wanted_keywords = get_wanted_keywords(WANTED_KW_PATH)
unwanted_keywords = get_unwanted_keywords(UNWANTED_KW_PATH)

