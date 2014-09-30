email-localization
==================

A command line tool to render HTML and text emails of markdown content.

## Requirements

1. Python 3.+
2. libxml - on OSX install with `xcode-select --install`

## Installation

`make install`

## Usage

`ks-email-parser` to generate all email templates

`ks-email-parser customerio [email_name]` to generate an email for customer.io service

### Options

Run `ks-email-parser --help` to see available options.

## Goal
The goal of storing emails in the following is to have a unified format that is easy to translate and to generate HTML and text emails equally. It also makes content formatting easy accords different languages.
Emails are defined as plain text or markdown for simple translation. The folder structure makes it easy to plug into an existing translation tool.

## Format

### Syntax

```
<?xml version="1.0" encoding="utf-8"?>
<resources template="html_template_name" style="css_style_name">
    <string
        name="template_placeholder_name"
        order="oder_for text conversion"
        >text_string</string>
</resources>
```
### Elements

#### `resource`
Resource attributes:

- **template** - the name of the corresponding HTML template to render
- **style** - (optional) comma separated value of CSS to be used for HTML templates. Those will be applied in order of the list.

#### `string`
Content formatting

- Plain text
- Markdown wrapped in `![CDATA[`

String attributes:

- **name** - Name of the matching place holder `[name_value]` in the HTML template
- **order** - (optional) in case of multiple string elements, they get rendered in the right order into text emails.

#### Example

```
<?xml version="1.0" encoding="UTF-8"?>
<resources template="basic_template.html" style="common.css,basic_template.css">
    <string name="subject">Verify your email address with KeepSafe.</string>
    <string name="content"><![CDATA[Hello,

    Please click the link below to verify your email address:

    ##[Verify email]({{url}})

    Thanks,
    The KeepSafe Team]]></string>
</resources>
```


## Templates

HTML templates use [Mustache](http://mustache.github.io/) to parse the template. You can use `{{name}}` inside a template and it will be replace by `name` string element from the email XML. You can find example of the templates in `templates_html` folder in this repo.


## Location

```
src/
    en/
        email_template.xml
templates_html/
    html_template.html
    html_template.css
```

- `src/` - all email content by local. e.g. `src/en/` for english content
- `templates_html/` - all HTML templates and CSS styles. A HTML template can have a corresponding CSS file with the same name.
