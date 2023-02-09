from html2image import Html2Image

hti = Html2Image()
hti.screenshot(
    html_file='index.html', css_file='style.css', save_as='page2.png', size=[(300, 200)]
)
