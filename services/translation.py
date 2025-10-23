from modeltranslation.translator import register, TranslationOptions
from .models import Category, City, Country, Event, EventImage, Discount

@register(Category)
class CategoryTranslationOptions(TranslationOptions):
    fields = ('name', 'description',)

@register(City)
class CityTranslationOptions(TranslationOptions):
    fields = ('name',)

@register(Country)
class CountryTranslationOptions(TranslationOptions):
    fields = ('name',)

@register(Event)
class EventTranslationOptions(TranslationOptions):
    fields = ('name', 'description',)

@register(EventImage)
class EventImageTranslationOptions(TranslationOptions):
    fields = ('alt_text',)

@register(Discount)
class DiscountTranslationOptions(TranslationOptions):
    fields = ('name',)