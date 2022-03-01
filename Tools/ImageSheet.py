class ImageSheet:
    def __init__(self, sheet, itemWidth, itemHeight):
        self.sheet = sheet
        self.images = []
        self.itemWidth = itemWidth
        self.itemHeight = itemHeight
        self.__processing()

    def __processing(self):
        sheetWidth = self.sheet.get_rect().width
        sheetHeight = self.sheet.get_rect().height
        self.countItemsWidth = int(sheetWidth / self.itemWidth)
        self.countItemsHeight = int(sheetHeight / self.itemHeight)

        for i in range(0, self.countItemsHeight):
            for j in range(0, self.countItemsWidth):
                startX = self.itemWidth * j
                startY = self.itemHeight * i
                tempImage = self.sheet.subsurface((startX, startY, self.itemWidth, self.itemHeight))
                self.images.append(tempImage)

    def getImages(self):
        return self.images

    def getImageWithRowAndColumn(self, row, column):
        startX = self.itemWidth * (column - 1)
        startY = self.itemHeight * (row - 1)
        return self.sheet.subsurface((startX, startY, self.itemWidth,
                                      self.itemHeight))
