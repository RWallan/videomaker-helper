from itertools import islice, pairwise
from pathlib import Path

from loguru import logger
from parsel.selector import Selector

from .audio import detect_silences

xml_template = """ <entry producer="{}" in="00:00:{:.3f}" out="00:00:{:.3f}">
   <property name="kdenlive:id">{}</property>
  </entry>
"""


def check_chain(
    filename: Path, input_file: Path, property: int | None = None
) -> tuple[str | None, ...]:
    with open(input_file) as f:
        content = f.read()
        s = Selector(content)

        if property:
            el = s.xpath(
                f"""
    //chain[(
        (./property[(@name='resource' and ./text()='{filename.name}')])
        and
        (./property[(@name='set.test_audio' and ./text()='{property}')])
    )]
"""
            )
        else:
            el = s.xpath(f'//chain/property[text() = "{filename.name}"]/..')

        _chain = el.css('chain::attr("id")').get()
        _id = el.css('property[name="kdenlive:id"]::text').get()

        playlists = s.xpath(
            f'//playlist/entry[@producer="{_chain}"]/..'
        ).xpath('@id')

        logger.debug(f'Playlists: {filename}-{playlists}')
        playlist_id = playlists.get()

        return _chain, _id, playlist_id


def write_file(silences, filename, chain, _id):
    logger.info('Start file', filename)

    with open(filename, 'w') as f:
        for start, stop in islice(pairwise(silences), 1, None, 2):
            if start < 0:
                start = 0.0
            f.write(xml_template.format(chain, start, stop, _id))

    logger.info('End file', filename)


def cut(audio_file, video_file, input_file, output_path: Path):
    times = detect_silences(str(audio_file))

    logger.info('Start video-video chain')
    chain_id, file_id, playlist = check_chain(video_file, input_file, 1)
    write_file(times, output_path / 'video.xml', chain_id, file_id)
    logger.info(f'Video playlist {playlist}')

    logger.info('Start video-audio chain')
    chain_id, file_id, playlist = check_chain(video_file, input_file, 0)
    write_file(times, output_path / 'video_audio.xml', chain_id, file_id)
    logger.info(f'Video playlist {playlist}')

    logger.info('Start audio chain')
    chain_id, file_id, playlist = check_chain(audio_file, input_file)
    write_file(times, output_path / 'audio.xml', chain_id, file_id)
    logger.info(f'Audio playlist {playlist}')
