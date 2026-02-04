from unittest import TestCase

from email_parser import renderer, config


class TestMarkdownExtensions(TestCase):
    def setUp(self):
        config.init(_base_img_path='images_base')

    def tearDown(self):
        config.init()

    def test_inline_text_block(self):
        html = renderer._md_to_html('[[#C0D9D9]]')
        self.assertEqual('#C0D9D9', html.strip())

    def test_base_url_image_is_rewritten(self):
        html = renderer._md_to_html('![Alt text](/path/to/img.jpg)', base_url='images_base')
        self.assertIn('src="images_base/path/to/img.jpg"', html)
        self.assertIn('style="max-width: 100%;"', html)

    def test_base_url_image_skips_absolute_url(self):
        html = renderer._md_to_html('![Alt text](http://example.com/img.jpg)', base_url='images_base')
        self.assertIn('src="http://example.com/img.jpg"', html)
        self.assertIn('style="max-width: 100%;"', html)
