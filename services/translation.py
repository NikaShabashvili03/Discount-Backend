from modeltranslation.translator import translator, TranslationOptions
from .models import City, Category

class CityTranslationOptions(TranslationOptions):
    fields = ('name',) 
translator.register(City, CityTranslationOptions)

class CategoryTranslationOptions(TranslationOptions):
    fields = ('name', 'description') 
translator.register(Category, CategoryTranslationOptions)
