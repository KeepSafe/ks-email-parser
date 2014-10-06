# ks-email-parser

A command line tool name `ks-email-parser` to render HTML and text emails of markdown content.

## Goal
The goal is to store emails in a unified format that is easy to translate and to generate HTML and text emails off. It should be easy for translators to maintain content formatting accords different languages.  

## Requirements

1. Python 3.+
2. libxml - on OSX install with `xcode-select --install`

## Installation

`make install`

## Usage

`ks-email-parser` in root folder to generate all emails.


### Options

Run `ks-email-parser --help` to see available options.


## Format
Emails are defined as plain text or markdown for simple translation. The folder structure makes it easy to plug into an existing translation tool.  
The content of each email is stored in a XML file that contains all content, the subject and the assosiated HTML template.

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


## Folder structure

```
src/
    en/
        email_template.xml
target/
templates_html/
    html_template.html
    html_template.css
```

- `src/` - all email content by local. e.g. `src/en/` for english content
- `target/` - Output folder generated. Contains the same local subfolders as `src/`. Each email generates 3 files with the self explained file extensions `.txt`, `.html` and `.subject`
- `templates_html/` - all HTML templates and CSS styles. A HTML template can have a corresponding CSS file with the same name.

## Rendering
*ks-email-parser* renders email content into HTML in 2 steps.

1. Render markdown files into simple HTML 
2. Inserting CSS style definitions from `html_template.css` inline into the HTML. The goal is to support email clients that don't support none inline CSS formatting.



## 3rd party support
Some 3rd party services have custom formates to represent emails in multiple languages. This is a list of supported providers.

### Customer.io
Customer.io defines their own multi language email format. More: [http://customer.io/docs/localization-i18n.html]()

#### Usage
`ks-email-parser customerio [email_name]`  
Generates a valid customer.io multi language email format into the `target/` folder.
