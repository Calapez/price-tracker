#Price Tracker

Price Tracker is an application to find promotions in online stores.
For now the application only works with the Worten website.

## Installation
Make sure Python 3 is installed.

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install the [scrapy](https://pypi.org/project/Scrapy/) library.

```bash
pip install scrapy
```

## Usage
If you want to filter the search, write the keywords you wish to include and/or exclude from the search in the respective files. The keywords must be separated by a newline.

```bash
scrapy runspider
```