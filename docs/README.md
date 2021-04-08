# Docs howto

## Compiling the documentation

### Prerequisites

You must install pandoc to build the nbsphinx examples:

```bash
wget https://github.com/jgm/pandoc/releases/download/2.11.4/pandoc-2.11.4-1-amd64.deb
sudo dpkg -i pandoc-2.11.4-1-amd64.deb
rm pandoc-2.11.4-1-amd64.deb
pandoc --version
```

### Without multiversion support

```bash
cd docs
make clean html
```

## With multiversion support

```bash
cd docs
sphinx-multiversion source/ build/html/
```

## Adding content to the documentation

The first page of the docs is `docs/source/index.rst`. From here all the other content is linked in `toctree`s. The content itself is collected in `docs/source/content`. API documentation is automatically collected by the `autodoc` sphinx extension.

The documentation is written in a markup language called [reStructuredText](https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html), which is similar to markdown.
