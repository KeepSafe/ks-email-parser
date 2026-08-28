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


class TestNoTrackingLinkProcessor(TestCase):
    def _render_link(self, source):
        html = markdown.markdown(source, extensions=[markdown_ext.no_tracking()])
        link = bs4.BeautifulSoup(html, 'html.parser').find('a')
        return html, link

    def test_strips_raw_bidi_marks_wrapping_link_target(self):
        _, link = self._render_link('[link](\u200e{{url}}\u200f)')

        self.assertEqual('{{url}}', link['href'])

    def test_strips_encoded_bidi_marks_wrapping_link_target(self):
        _, link = self._render_link('[link](%E2%80%8F{{url}}%E2%80%8E)')

        self.assertEqual('{{url}}', link['href'])

    def test_preserves_bidi_marks_inside_link_target(self):
        src = 'https://example.com/a%E2%80%8Eb?q=%E2%80%8Fvalue'

        _, link = self._render_link(f'[link]({src})')

        self.assertEqual(src, link['href'])

    def test_preserves_encoded_reserved_url_components(self):
        src = 'https://example.com/a%2Fb?q=x%26y%3Fz#part%23value'

        _, link = self._render_link(f'[link]({src})')

        self.assertEqual(src, link['href'])

    def test_applies_no_tracking_after_stripping_bidi_wrappers(self):
        _, link = self._render_link('[link](\u200e!{{url}}\u200e)')

        self.assertEqual('{{url}}', link['href'])
        self.assertEqual('off', link['clicktracking'])


class TestLegacyStrongProcessor(TestCase):
    def _render(self, source):
        return markdown.markdown(
            source,
            extensions=[markdown_ext.no_tracking(), markdown_ext.legacy_strong()],
        )

    def test_preserves_markdown_2_strong_delimiter_behavior(self):
        cases = {
            'multiline closing delimiter': (
                '**[Verify your email now]({{url}})\n** so we know',
                '<p><strong><a href="{{url}}">Verify your email now</a>\n</strong> so we know</p>',
            ),
            'leading delimiter whitespace': (
                '** Sign-up and manage**',
                '<p><strong> Sign-up and manage</strong></p>',
            ),
            'trailing delimiter whitespace': (
                '**[link]({{url}}) **',
                '<p><strong><a href="{{url}}">link</a> </strong></p>',
            ),
            'nested emphasis': (
                '*Arabic text **strong text** suffix*',
                '<p><em>Arabic text <strong>strong text</strong> suffix</em></p>',
            ),
            'literal footnote marker': (
                'page*. Please act **within 24 hours**.',
                '<p>page*. Please act <strong>within 24 hours</strong>.</p>',
            ),
        }

        for name, (source, expected) in cases.items():
            with self.subTest(name=name):
                self.assertEqual(expected, self._render(source))

    def test_preserves_valid_strong_and_emphasis(self):
        source = 'before **bold** after *em*'

        self.assertEqual(
            '<p>before <strong>bold</strong> after <em>em</em></p>',
            self._render(source),
        )

    def test_leaves_underscore_emphasis_to_markdown_3_processor(self):
        source = 'Icon changes from _____ to _____.'

        self.assertEqual(
            '<p>Icon changes from <strong><em>_</em> to </strong>___.</p>',
            self._render(source),
        )
