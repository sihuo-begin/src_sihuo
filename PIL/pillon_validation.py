from PIL import Image, ImageOps
image = Image.open("sample2.jpg")
image.show()
gray_image = ImageOps.grayscale(image)

bw_image = gray_image.point(lambda x: 0 if x <105 else 144, "1")
bw_image.show()
