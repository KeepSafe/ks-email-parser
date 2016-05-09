# ks-email-parser [![Build Status](https://travis-ci.org/KeepSafe/ks-email-parser.svg?branch=master)](https://travis-ci.org/KeepSafe/ks-email-parser)

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
        order="order_for text conversion"
        >text_string</string>
</resources>
```

#### Inline text

By default any text simple text you put in a `<string>` tag will be wrapped in a `<p>` tag, so `simple text` would become `<p>simple text</p>`.
This is standard markdown behaviour. In case you want to get raw text output, for example if you want to use it in a link tag,
wrap the entire block in `[[text]]`, for example `<string name="link">[[www.google.pl]]</string>` would become `www.google.pl`.
This is true only for entire blocks of text (paragraphs separated by blanck lines), `<string name="link">[[www.google.pl]] hello</string>`
would be rendered as `[[www.google.pl]] hello`

#### Base url for images

The parser will automatically add base_url to any image tag in markdown, so `![Alt text](/path/to/img.jpg)` and base url `base_url`
will produce `<img alt="Alt text" src="base_url/path/to/img.jpg" />`

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

HTML templates use [Mustache](http://mustache.github.io/) to parse the template. You can use `{{name}}` inside a template and it will be replace by `name` string element from the email XML or you can use `{{global_name}}` and it will be replaced  by `name` string elemenet from `<lang>/global.xml` (this file has exactly the same structure as usual email XML and behaviour, except it won't be parsed). You can find example of the templates in `templates_html` folder in this repo.


## Folder structure

```
src/
    en/
        email_template.xml
    global.xml
target/
templates_html/
    html_template.html
    html_template.css
```

- `src/` - all email content by local. e.g. `src/en/` for english content
- `target/` - Output folder generated. Contains the same local subfolders as `src/`. Each email generates 3 files with the self explained file extensions `.txt`, `.html` and `.subject`
- `templates_html/` - all HTML templates and CSS styles. A HTML template can have a corresponding CSS file with the same name.

This structure is configurable. By changing `source`, `destination`, `templates` and `pattern` you can use a structure you like. The `pattern` parameter is especially useful as it controls directory layout and email names. the default is `{locale}/{name}.xml` but you can use `{name}.{locale}.xml` if you don't want to have nested directories. Keep in mind both `name` and `locale` are required in the pattern.

## Rendering
*ks-email-parser* renders email content into HTML in 2 steps.

1. Render markdown files into simple HTML
2. Inserting CSS style definitions from `html_template.css` inline into the HTML. The goal is to support email clients that don't support inline CSS formatting.

### Strict mode

You can use `--strict` option to make sure all placeholders are filled. If there are leftover placeholders the parsing will fail with an error.

### isText

In case you want to put some non-text values in emails, like colors, you can use placeholders which will be ignored in text emails:

`<string name="color" isText="false">[[#C0D9D9]]</string>`

The only valid false value for isText is `false`, everything else counts as true including omitting the attribute.

## Placeholders validation

To make sure the placeholders are consistent between languages and every language has all needed placeholders you can create configuration file to hold needed placeholders.

### Config file

The file is a mapping of name to required placeholders and the number of times they appear. It's a json file with structure as below:

```
{
    "email name" : {"placeholder1":1, "placeholder2":2}
}
```

You can generate the file in the provided source directory from existing emails with 

```
$ ks-email-parser config placeholders
```

It will go through your email and extract placeholders.

### Validation

If the config file is present in the source directory each email will be validated for having placeholders specified in the file. The parsing will fail with an error if any email is missing one of required placeholders.

## 3rd party support
Some 3rd party services have custom formats to represent emails in multiple languages. This is a list of supported providers.

### Customer.io
Customer.io defines their own multi language email format. More: [http://customer.io/docs/localization-i18n.html](http://customer.io/docs/localization-i18n.html)

#### Usage
`ks-email-parser customerio [email_name]`  
Generates a valid customer.io multi language email format into the `target/` folder.
