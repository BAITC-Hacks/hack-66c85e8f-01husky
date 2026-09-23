# Подключение Kenes AI: Fireflies, гости и SDK

Проверено 23 сентября 2026. Обязательные платформы: Google Meet, Zoom, Microsoft Teams. Никита выбрал гостевой вход с допуском организатора.

## Что известно о Fireflies

| Платформа | Что описывает Fireflies | Следствие для Kenes AI |
|---|---|---|
| Meet | Бот входит гостем. Организация должна разрешать незалогиненных участников; host допускает бота, в том числе из списка потенциальных рисков | Проверять доступ гостя и фактический ответ встречи |
| Teams | Гостевой вход зависит от anonymous-join policies; проверка личности и CAPTCHA могут помешать. Бот может попасть в lobby с предупреждением | Ожидать допуска, различать запрет гостя и ошибку клиента |
| Zoom | Есть OAuth-интеграция. Инструкция требует разрешить гостей web-клиента; waiting room требует допуска, если включена | Ссылка сама по себе не гарантирует вход; host должен разрешать выбранный способ подключения |

Источники: [Fireflies: Meet](https://guide.fireflies.ai/articles/7581948912-how-to-invite-fireflies-to-google-meet-meetings), [Fireflies: Teams](https://guide.fireflies.ai/articles/1095228584-how-to-invite-fireflies-to-microsoft-teams-meeting), [Fireflies: Zoom](https://guide.fireflies.ai/articles/8956173738-how-to-integrate-zoom-with-fireflies).

Приглашение `fred@fireflies.ai` и подключённый календарь помогают сервису найти встречу и время старта. Они не подтверждают право входа в закрытую встречу. Fireflies отдельно перечисляет неуспех из-за обязательной авторизации, отказа host, CAPTCHA и ограничений домена. [Диагностика Fireflies](https://guide.fireflies.ai/articles/4708529470-why-fred-did-not-join-your-meeting-troubleshooting-guide).

Публичные инструкции не раскрывают весь внутренний транспорт Fireflies. По ним нельзя утверждать, что сервис использует именно Playwright либо одинаковую реализацию на всех платформах.

## Официальные способы получить медиа

| Способ | Условия | Решение для текущей реализации |
|---|---|---|
| Zoom RTMS | Авторизованное приложение, доступ к RTMS и настройка аккаунта. Есть media и active-speaker events | Официальный путь для будущей интеграции; текущая реализация использует гостевой web-клиент |
| Teams application-hosted media bot | Специальный media SDK; production deployment требует Windows Server в Azure | Не помещается в текущий общий Linux worker; нужен отдельный runtime и регистрация |
| Google Meet Media API | Developer Preview; project, OAuth principal и участники должны соответствовать условиям программы | Не заменяет универсальный гостевой бот для произвольной встречи |

Документация Zoom Meeting SDK для Linux теперь указывает, что AI-notetakers должны использовать RTMS; SDK не выбирается для нового бота. Источники: [Zoom SDK policy](https://developers.zoom.us/docs/meeting-sdk/linux/), [RTMS](https://developers.zoom.us/docs/rtms/meetings/), [Teams media bot requirements](https://learn.microsoft.com/en-us/microsoftteams/platform/bots/calls-and-meetings/requirements-considerations-application-hosted-media-bots), [Meet Media API](https://developers.google.com/workspace/meet/media-api/guides/get-started).

## Фактическая проверка Kenes AI

Тестовые приглашения хранятся вне репозитория. Гостевые сессии не используют личный профиль Chrome.

- Meet вернул `You can't join this video call` до формы имени. Причина не установлена: по одному сообщению нельзя приписать отказ настройкам host.
- Zoom: бот заполнил имя и нажал Join. После исправления блокировки публичного Google iframe сервис ответил `Automated bots aren't allowed to join this meeting` и предложил авторизацию. Гостевой вход в эту встречу не подтверждён; следующий путь интеграции требует настройки RTMS-приложения и доступа аккаунта.
- Teams: автоматический ввод имени и вход подтверждены controls действующего звонка; Никита подтвердил принятого участника скриншотом.
- Повторный запуск видимого Chrome завершился закрытием браузера (`TargetClosedError`); он не подтверждает ни разрешение, ни запрет входа.
- Полный автоматический запуск заполнил `Kenes AI` и нажал вход в Teams и Zoom. Никита подтвердил подключение бота скриншотом: виден Kenes AI (Guest) и тестовая камера Chromium. Статус встречи проверяется дополнительными controls, одной кнопки Leave недостаточно.
- Слышимой записи реального звонка с загрузкой в backend пока нет.
- По сообщению Никиты тестовые камера и микрофон давали анимацию и звук. Тестовые источники заменены светлым логотипом из develop и нулевым WAV. Локальный native WebRTC тест подтвердил 1920×1080 на принимающей стороне, нулевые сэмплы и неизменность кадра. В живом Teams исходник 1920×1080 согласован до 1280×720 при 25 fps; исходящий RTP подтверждает передачу 1280×720. Передача 1080p в Teams не подтверждена. Зеркальный собственный preview не отражает ориентацию у других участников: полученный кадр имеет обычную ориентацию.

## Как автоматизируют вход другие разработчики

Recall.ai принимает `meeting_url` и `bot_name` при создании бота. Attendee использует тот же контракт. Пользователь не заполняет форму имени внутри звонка: это делает адаптер платформы. Для встреч с обязательным login оба сервиса предусматривают signed-in bots. [Recall API](https://docs.recall.ai/reference/bot_create), [Attendee API](https://docs.attendee.dev/api-reference/tag/bots/post/api/v1/bots), [Attendee signed-in bots](https://docs.attendee.dev/guides/signedinbots).

Изучен открытый код Attendee, commit `0b0d6973b7182f764a15f8c9c45c5c48bb0dcae5`: [Meet prejoin и admission](https://github.com/attendee-labs/attendee/blob/0b0d6973b7182f764a15f8c9c45c5c48bb0dcae5/bots/google_meet_bot_adapter/google_meet_ui_methods.py), [Teams prejoin и admission](https://github.com/attendee-labs/attendee/blob/0b0d6973b7182f764a15f8c9c45c5c48bb0dcae5/bots/teams_bot_adapter/teams_ui_methods.py). По наблюдаемым UI controls добавлены варианты кнопок Meet, подтверждение уведомления о записи и дополнительная проверка допуска. Проверки не используют сторонний сервис для обработки записей.

## Приёмка

Для каждой платформы отдельно: форма имени → заявка на вход → host допускает → бот виден как `Kenes AI` → минута тестовой речи → завершение → валидный слышимый WAV → однократный callback → meeting в `draft`. Сопоставить речь в записи с ожидаемым содержимым. Локальные HTML fixtures проверяют код управления состояниями, но не доказывают совместимость с текущим сервисом.

Дополнительные проверки: отказ host, истечение ожидания, обязательный login, security challenge, исчезновение браузера, остановка ffmpeg. При CAPTCHA или обязательном login бот сообщает ограничение. Учётная сессия или SDK требуют отдельного согласованного подключения.

## События активного спикера

Zoom RTMS присылает active-speaker event с timestamp/user_id/user_name. Событие обозначает основного говорящего; оно не перечисляет всех людей, говорящих одновременно. [Event reference](https://godevelopers.zoom.us/docs/rtms/event-reference/). Meet Media API связывает audio CSRC с участником, но действует ограничение Developer Preview. [MediaEntry](https://developers.google.com/workspace/meet/media-api/reference/dc/media_api.mediaentry).

Для гостевого web-бота текущий кандидат: фиксировать наблюдаемые индикаторы активности как подсказки с явным происхождением `dom`, временем относительно аудио и погрешностью. Имя в платформе не подтверждает личность. При недоступном индикаторе, перекрытии речи или разрыве наблюдения сохранять неизвестность. Исследование выполнено; контракт, сбор событий и передача в backend ещё не реализованы. Текущий PR не добавляет данные активного спикера.

## Передача команде, 23 сентября 2026

По просьбе Никиты текущий срез передаётся в PR до полной живой приёмки всех платформ. Код синхронизирован с `develop` (`54ea63f`, merge `7d7a781`, включая интеграцию frontend с backend из PR #6).

Локальный `scripts/check.sh` после объединения: backend 96, pipeline 19, bots 79 тестов; Ruff и HTTP smoke прошли. Native WebRTC тесты используют установленный Chrome (`KENES_TEST_BROWSER_CHANNEL=chrome`). Это не подтверждает полный запуск контейнерного стека.

| Область | Что может делать команда |
|---|---|
| Backend/frontend | Интегрировать создание bot-meeting и состояния обработки по текущему API; проверять ошибки и повторный запуск |
| Pipeline, Ардак | Продолжать обработку загруженного WAV; метаданных активного спикера в callback пока нет |
| Bots, агент B | Завершить Linux PulseAudio smoke и запись реальной встречи с callback; диагностировать доступ Meet; подготовить Zoom RTMS после получения доступа |
| BOT5, агент B | Согласовать контракт временной шкалы, происхождение и погрешность наблюдений; затем реализовать передачу подсказок о спикерах |

Открыто: слышимая запись реальной встречи → callback → draft; сборка и запуск bot-runtime; гостевой вход Meet; Zoom RTMS; активные спикеры. Телемост остаётся опциональным. При передаче владения файлами согласовать это с агентом B.

## Диагностика Meet после PR #8

PR #8 влит в develop. Следующий срез исправляет вход на страницу prejoin, но не заявляет успешное подключение.

На одной тестовой встрече и одном Chrome проверено:

| Вариант | Результат |
|---|---|
| Исходный Playwright launch | `ResolveMeetingSpace` возвращает HTTP 403 до формы имени |
| Без request/WebSocket guard | Тот же отказ |
| Без guard и media init script | Тот же отказ |
| С восстановленными component extensions | Тот же отказ |
| Только исключён `--enable-automation` | Тот же отказ; `navigator.webdriver` остаётся true |
| Meet с `--disable-blink-features=AutomationControlled` | `ResolveMeetingSpace` 200, поле имени доступно; после заявки `CreateMeetingDevice` 403 |
| Отдельно запущенный Chrome с чистым профилем и CDP | Форма имени доступна; после заявки тот же отказ |

В production добавлен один параметр только для Meet. Sandbox, ограничения сетевых адресов, гостевой профиль, имя Kenes AI и допуск организатора сохранены. Это исправление первого этапа; оно не гарантирует вход во встречу. Общий отказ `can't join` теперь не приписывается организатору без доказательства.

На присланном организатором скриншоте выбран Trusted и включено разрешение запросить вход. Экран также сообщает, что настройки относятся к будущим запускам. Для следующего контрольного прогона запрошена новая встреча или перезапуск текущей. Публичные документы не позволяют установить причину второго 403 по одному коду.

### Какие решения используют другие

- Google описывает вход без аккаунта через имя и запрос организатору. Отключение knocking автоматически отклоняет анонимов. [Вход](https://support.google.com/meet/answer/9303069?co=GENIE.Platform%3DDesktop&hl=en), [настройки доступа](https://support.google.com/a/users/answer/11989526?hl=en).
- Recall сохраняет гостевой режим для разрешающих его встреч. Для закрытых встреч предлагает отдельный платный Workspace с SSO; имя берётся из аккаунта. [Guest FAQ](https://docs.recall.ai/docs/google-meet-faq), [signed-in setup](https://docs.recall.ai/docs/google-meet-login-getting-started).
- Attendee также использует отдельный Workspace и SAML SSO для signed-in Meet, поддерживает self-hosted адрес IdP. Это отдельный путь интеграции, требующий настройки аккаунта. [Инструкция](https://docs.attendee.dev/guides/signedinbots).
- В открытом коде Attendee и Vexa есть headed launch и изменения automation flags; оба также меняют другие свойства браузера. Их код сам по себе не доказывает причину нашего отказа. [Attendee](https://github.com/attendee-labs/attendee/blob/0b0d6973b7182f764a15f8c9c45c5c48bb0dcae5/bots/web_bot_adapter/web_bot_adapter.py#L756-L797), [Vexa](https://github.com/Vexa-ai/vexa/blob/dba990b413bd0f888b02d46a24f802db492addbb/core/meetings/modules/remote-browser/src/browser.ts#L35-L46).

Выбор для текущего этапа: довести гостевой вход на контрольной встрече. Если её доступ требует аккаунт, отдельно согласовать выделенную учётную запись Kenes AI. Meet Media API пока не подходит для произвольных встреч из-за требований Developer Preview к участникам.
