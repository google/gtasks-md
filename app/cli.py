import pandoc

from .googleapi import GoogleApiService
from .pandoc import toPandoc


def main():
    service = GoogleApiService()
    taskLists = service.getTaskLists()
    doc = toPandoc(taskLists)
    str = pandoc.write(doc)
    print(str)


if __name__ == "__main__":
    main()
