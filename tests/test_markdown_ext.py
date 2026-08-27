from unittest import TestCase

import bs4
import markdown

from email_parser import markdown_ext


class TestBaseUrlImageProcessor(TestCase):
    def _render_image(self, source, images_dir):
        html = markdown.markdown(source, extensions=[markdown_ext.base_url(images_dir)])
        image = bs4.BeautifulSoup(html, 'html.parser').find('img')
        self.assertEqual('max-width: 100%;', image['style'])
        return html, image['src']

    def test_preserves_encoded_absolute_url_components(self):
        src = (
            'https://cdn.example.com/a%2Fb/image%20name-%7Bvalue%7D.png'
            '?next=%2Fhome%3Ftab%3Done%26x%3Dtwo#part%2Fone'
        )

        html, actual_src = self._render_image(f'![Alt]({src})', 'https://assets.example.com/images')

        self.assertEqual(src, actual_src)
        self.assertEqual(f'<p><img alt="Alt" src="{src}" style="max-width: 100%;" /></p>', html)

    def test_preserves_encoded_ftp_url(self):
        src = 'ftp://files.example.com/a%2Fb/image%20name.png?token=%7Bvalue%7D#part%2Fone'

        _, actual_src = self._render_image(f'![Alt]({src})', 'https://assets.example.com/images')

        self.assertEqual(src, actual_src)

    def test_prefixes_relative_encoded_path(self):
        html, actual_src = self._render_image(
            '![Alt](/path/image%20name.png)',
            'https://assets.example.com/images/',
        )

        expected_src = 'https://assets.example.com/images/path/image%20name.png'
        self.assertEqual(expected_src, actual_src)
        self.assertEqual(f'<p><img alt="Alt" src="{expected_src}" style="max-width: 100%;" /></p>', html)

    def test_normalizes_relative_path_without_images_dir(self):
        html, actual_src = self._render_image('![Alt](/path/image.png)', '')

        self.assertEqual('path/image.png', actual_src)
        self.assertEqual('<p><img alt="Alt" src="path/image.png" style="max-width: 100%;" /></p>', html)

    def test_normalizes_only_encoded_spaces_in_placeholder(self):
        html, actual_src = self._render_image('![Alt]({{ image_url }})', 'https://assets.example.com/images')

        self.assertEqual('{{ image_url }}', actual_src)
        self.assertEqual('<p><img alt="Alt" src="{{ image_url }}" style="max-width: 100%;" /></p>', html)

    def test_preserves_ordinary_absolute_url(self):
        src = 'https://example.com/path/image.png?size=large#hero'

        html, actual_src = self._render_image(f'![Alt]({src})', 'https://assets.example.com/images')

        self.assertEqual(src, actual_src)
        self.assertEqual(f'<p><img alt="Alt" src="{src}" style="max-width: 100%;" /></p>', html)
