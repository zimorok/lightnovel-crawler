# -*- coding: utf-8 -*-
import io
import logging
import os
import re
import base64

try:
    from ebooklib import epub
except Exception as err:
    logging.fatal('Failed to import `ebooklib`')
# end try

logger = logging.getLogger('EPUB_BINDER')


def make_cover_image(app):
    if not (app.book_cover and os.path.isfile(app.book_cover)):
        return None
    # end if
    logger.info('Creating cover: %s', app.book_cover)
    ext = app.book_cover.split('.')[-1]
    cover_image = epub.EpubImage()
    cover_image.uid = 'cover'
    cover_image.file_name = 'cover.%s' % ext
    cover_image.media_type = 'image/%s' % ext
    with open(app.book_cover, 'rb') as image_file:
        cover_image.content = image_file.read()
    # end with
    return cover_image
# end def


def make_intro_page(app, cover_image):
    logger.info('Creating intro page')
    source_url = app.crawler.home_url or 'Unknown'
    github_url = 'https://github.com/dipu-bd/lightnovel-crawler'

    intro_html = '<div style="%s">' % ';'.join([
        'min-height: 6.5in',
        'display: flex',
        'text-align: center',
        'flex-direction: column',
        'justify-content: space-between',
    ])

    intro_html += '''
        <div>
            <h1>%s</h1>
            <h3>%s</h3>
        </div>
    ''' % (
        app.crawler.novel_title or 'N/A',
        app.crawler.novel_author or 'N/A',
    )

    if cover_image:
        intro_html += '<img id="cover" src="%s" style="%s">' % (
            cover_image.file_name, '; '.join([
                'max-height: 65%',
                'min-height: 3.0in',
                'object-fit: contain',
                'object-position: center center'
            ]))
    # end if

    intro_html += '''
    <div>
        <b>Source:</b> <a href="%s">%s</a><br>
        <i>Generated by <b><a href="%s">Lightnovel Crawler</a></b></i>
    </div>''' % (source_url, source_url, github_url)

    intro_html += '</div>'

    return epub.EpubHtml(
        uid='intro',
        file_name='intro.xhtml',
        title='Intro',
        content=intro_html,
    )
# end def


def make_chapters(book, chapters):
    toc = []
    volume = []
    for i, chapter in enumerate(chapters):
        xhtml_file = 'chap_%s.xhtml' % str(i + 1).rjust(5, '0')
        content = epub.EpubHtml(
            # uid=str(i + 1),
            file_name=xhtml_file,
            title=chapter['title'],
            content=chapter['body'] or '',
        )
        book.add_item(content)
        volume.append(content)
        book.spine.append(content)
        # separate chapters by volume
        if i + 1 == len(chapters) or chapter['volume'] != chapters[i + 1]['volume']:
            toc.append((
                epub.Section(chapter['volume_title'],
                             href=volume[0].file_name),
                tuple(volume)
            ))
            volume = []
        # end if
    # end for
    book.toc = tuple(toc)
# end def


def bind_epub_book(app, chapters, volume=''):
    book_title = (app.crawler.novel_title + ' ' + volume).strip()
    logger.debug('Binding epub: %s', book_title)

    # Create book
    book = epub.EpubBook()
    book.set_language('en')
    book.set_title(book_title)
    book.add_author(app.crawler.novel_author)
    book.set_identifier(app.output_path + volume)

    # Create intro page
    cover_image = make_cover_image(app)
    if cover_image:
        book.add_item(cover_image)
    # end if
    intro_page = make_intro_page(app, cover_image)
    book.add_item(intro_page)

    # Create book spine
    try:
        book.set_cover('image.jpg', open(app.book_cover, 'rb').read())
        book.spine = ['cover', intro_page, 'nav']
    except Exception:
        book.spine = [intro_page, 'nav']
        logger.warn('No cover image')
    # end if

    # Create chapters
    make_chapters(book, chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # Save epub file
    epub_path = os.path.join(app.output_path, 'epub')
    file_name = app.good_file_name
    if not app.no_append_after_filename:
        file_name += ' ' + volume
    # end if
    file_path = os.path.join(epub_path, file_name + '.epub')
    logger.debug('Writing %s', file_path)
    os.makedirs(epub_path, exist_ok=True)
    epub.write_epub(file_path, book, {})
    print('Created: %s.epub' % file_name)
    return file_path
# end def


def make_epubs(app, data):
    epub_files = []
    for vol in data:
        if len(data[vol]) > 0:
            book = bind_epub_book(
                app,
                volume=vol,
                chapters=data[vol],
            )
            epub_files.append(book)
        # end if
    # end for
    return epub_files
# end def
