from telegram.ext import ConversationHandler

# Состояния для регистрации
(
    ASK_GENDER,
    ASK_AGE,
    ASK_CITY,
    ASK_BIO,
    ASK_PHOTO,
    ASK_SEARCH_GENDER,
    ASK_SEARCH_AGE_MIN,
    ASK_SEARCH_AGE_MAX,
    ASK_SEARCH_DISTANCE,
    ASK_LOCATION
) = range(10)
