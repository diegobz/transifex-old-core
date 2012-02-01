from django import template
from django.db.models import Sum
from transifex.languages.models import Language
from transifex.resources.models import RLStats
from transifex.txcommon.utils import StatBarsPositions

register = template.Library()

@register.inclusion_tag('resources/stats_bar_simple.html')
def progress_for_project(project, language_code=None, width=100):
    """Render a progressbar for the specified project."""

    stats = RLStats.objects.filter(
        resource__project=project, language__code=language_code
    ).values('language__code').distinct().annotate(
        mytranslated=Sum('translated'), myuntranslated=Sum('untranslated')
    ).filter()

    if not stats:
        # Project has no resources
        bar_data = [
            ('trans', 0),
            ('untrans', 100)
        ]
        return {
            'untrans_percent': 100,
            'trans_percent': 0,
            'untrans': 0,
            'trans': 0,
            'pos': StatBarsPositions(bar_data, width),
            'width': width
        }
    stats = stats[0]

    translated = stats['mytranslated']
    untranslated = stats['myuntranslated']
    total = translated + untranslated

    try:
        translated_perc = translated * 100 / total
    except ZeroDivisionError:
        translated_perc = 100

    untranslated_perc = 100 - translated_perc

    bar_data = [
        ('trans', translated_perc),
        ('untrans', untranslated_perc)
    ]

    return {
        'untrans_percent': untranslated_perc,
        'trans_percent': translated_perc,
        'untrans': untranslated,
        'trans': translated,
        'pos': StatBarsPositions(bar_data, width),
        'width': width
    }
