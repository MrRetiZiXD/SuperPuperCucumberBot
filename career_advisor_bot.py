
#  KODLAND - ВСЕГДА БЫЛИ И БУДУТ ЛУЧШЕЙ ШКОЛОЙ ДЛЯ ПРОГРАММИСТОВ! 👍

import os
import sqlite3
import json
import requests
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, ConversationHandler, ContextTypes, filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "8474132149:AAHIinr4CEV53oYLZVnwu3pcxqQNrVxcWck")
DB_PATH = "career_advisor.db"
HH_API_URL = "https://api.hh.ru/vacancies"

(AGE_GROUP, EDUCATION, INTERESTS, SKILLS, CURRENT_JOB, 
 SATISFACTION, TEST_QUESTION, SEARCH_QUERY, TEST_ANSWER) = range(9)

CAREER_CATEGORIES = {
    "IT": "IT и технологии",
    "CREATIVE": "Творчество и дизайн", 
    "BUSINESS": "Бизнес и управление",
    "SCIENCE": "Наука и образование",
    "MEDICAL": "Медицина и здоровье",
    "TECHNICAL": "Рабочие специальности",
    "SERVICE": "Сфера услуг"
}

def init_database():
    """Инициализация базы данных с расширенной схемой"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY,
        first_name TEXT,
        username TEXT,
        age_group TEXT,
        education TEXT,
        interests TEXT,
        skills TEXT,
        current_job TEXT,
        satisfaction INTEGER,
        created_at TEXT,
        updated_at TEXT
    )""")
    
    c.execute("""
    CREATE TABLE IF NOT EXISTS careers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT,
        description TEXT,
        skills_required TEXT,
        education_level TEXT,
        salary_range TEXT,
        tags TEXT,
        learning_resources TEXT,
        created_at TEXT
    )""")
    
    c.execute("""
    CREATE TABLE IF NOT EXISTS test_questions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_text TEXT NOT NULL,
        options TEXT NOT NULL,
        weights TEXT NOT NULL,
        category TEXT,
        order_num INTEGER
    )""")
    
    c.execute("""
    CREATE TABLE IF NOT EXISTS user_test_results(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        category TEXT,
        score INTEGER,
        test_date TEXT,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS interactions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT,
        details TEXT,
        timestamp TEXT,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )""")
    
    c.execute("""
    CREATE TABLE IF NOT EXISTS parsed_vacancies(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT,
        vacancy_data TEXT,
        created_at TEXT,
        expires_at TEXT
    )""")
    
    conn.commit()
    conn.close()

def seed_careers():
    """Заполнение базы данных профессиями"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM careers")
    if c.fetchone()[0] > 0:
        conn.close()
        return
    
    careers_data = [
        ("Frontend разработчик", "IT и технологии", 
         "Создание пользовательских интерфейсов для веб-сайтов и приложений. Работа с HTML, CSS, JavaScript и современными фреймворками.",
         "JavaScript,HTML,CSS,React,Vue.js,TypeScript", "ВУЗ/Курсы", "80000-200000",
         "программирование,веб,дизайн,интерфейсы", "https://learn.javascript.ru/,https://react.dev/"),
        
        ("Backend разработчик", "IT и технологии",
         "Разработка серверной части приложений, работа с базами данных, API и бизнес-логикой.",
         "Python,Java,C#,Node.js,SQL,PostgreSQL", "ВУЗ/Курсы", "90000-250000",
         "программирование,сервер,базы данных,api", "https://docs.python.org/,https://spring.io/"),
        
        ("Data Scientist", "IT и технологии",
         "Анализ больших данных, создание моделей машинного обучения и извлечение инсайтов из информации.",
         "Python,R,SQL,машинное обучение,статистика", "ВУЗ", "120000-300000",
         "данные,аналитика,машинное обучение,статистика", "https://scikit-learn.org/,https://pandas.pydata.org/"),
        
        ("DevOps инженер", "IT и технологии",
         "Автоматизация процессов разработки, настройка инфраструктуры и обеспечение непрерывной интеграции.",
         "Docker,Kubernetes,AWS,Linux,CI/CD", "ВУЗ/Курсы", "100000-280000",
         "автоматизация,инфраструктура,облако,мониторинг", "https://kubernetes.io/,https://docs.docker.com/"),
        
        ("QA тестировщик", "IT и технологии",
         "Тестирование программного обеспечения, поиск ошибок и обеспечение качества продукта.",
         "тестирование,автоматизация,Selenium,Postman", "Курсы/Опыт", "60000-150000",
         "тестирование,качество,автоматизация,баг-репорты", "https://www.selenium.dev/,https://postman.com/"),
        
        ("Системный администратор", "IT и технологии",
         "Поддержка IT-инфраструктуры, настройка серверов и обеспечение стабильной работы систем.",
         "Linux,Windows,сети,безопасность,мониторинг", "ВУЗ/Курсы", "70000-180000",
         "администрирование,серверы,сети,безопасность", "https://www.redhat.com/,https://ubuntu.com/"),
        
        ("UX/UI дизайнер", "Творчество и дизайн",
         "Проектирование пользовательского опыта и создание удобных интерфейсов для цифровых продуктов.",
         "Figma,Sketch,Adobe XD,прототипирование,исследования", "Курсы/Портфолио", "80000-200000",
         "дизайн,интерфейсы,пользовательский опыт,креатив", "https://www.figma.com/,https://uxdesign.cc/"),
        
        ("Графический дизайнер", "Творчество и дизайн",
         "Создание визуальных материалов: логотипы, плакаты, упаковка, брендинг и рекламные материалы.",
         "Photoshop,Illustrator,InDesign,типографика,брендинг", "Курсы/Портфолио", "50000-150000",
         "дизайн,графика,брендинг,креатив,реклама", "https://www.adobe.com/,https://www.behance.net/"),
        
        ("Веб-дизайнер", "Творчество и дизайн",
         "Создание дизайна веб-сайтов, работа с макетами и адаптивным дизайном.",
         "Figma,Photoshop,HTML,CSS,адаптивный дизайн", "Курсы/Портфолио", "60000-160000",
         "дизайн,веб,интерфейсы,креатив,макеты", "https://www.figma.com/,https://webflow.com/"),
        
        ("Контент-мейкер", "Творчество и дизайн",
         "Создание контента для социальных сетей, блогов и маркетинговых кампаний.",
         "копирайтинг,фото,видео,SMM,креативность", "Опыт/Курсы", "40000-120000",
         "контент,социальные сети,креатив,маркетинг", "https://canva.com/,https://www.instagram.com/"),
        
        ("Видеомонтажер", "Творчество и дизайн",
         "Монтаж видео, создание роликов для YouTube, рекламы и корпоративного контента.",
         "Premiere Pro,After Effects,DaVinci Resolve,цветокоррекция", "Курсы/Опыт", "50000-150000",
         "видео,монтаж,креатив,постпродакшн", "https://www.adobe.com/,https://www.blackmagicdesign.com/"),
        
        ("Менеджер проектов", "Бизнес и управление",
         "Планирование и координация проектов, управление командой и контроль сроков выполнения.",
         "планирование,управление,команда,коммуникации,Agile", "ВУЗ/Курсы", "80000-200000",
         "управление,проекты,команда,планирование", "https://www.pmi.org/,https://scrum.org/"),
        
        ("Маркетолог", "Бизнес и управление",
         "Разработка маркетинговых стратегий, продвижение продуктов и анализ рынка.",
         "аналитика,реклама,SMM,контент-маркетинг,SEO", "ВУЗ/Курсы", "70000-180000",
         "маркетинг,реклама,аналитика,продвижение", "https://www.google.com/analytics/,https://ads.google.com/"),
        
        ("HR-менеджер", "Бизнес и управление",
         "Подбор персонала, работа с сотрудниками, развитие корпоративной культуры.",
         "рекрутинг,психология,коммуникации,оценка персонала", "ВУЗ/Курсы", "60000-150000",
         "персонал,рекрутинг,психология,управление", "https://www.linkedin.com/,https://hh.ru/"),
        
        ("Бизнес-аналитик", "Бизнес и управление",
         "Анализ бизнес-процессов, выявление проблем и предложение решений для оптимизации.",
         "аналитика,Excel,SQL,процессы,документация", "ВУЗ", "80000-200000",
         "аналитика,бизнес,процессы,оптимизация", "https://www.microsoft.com/excel/,https://www.tableau.com/"),
        
        ("Продакт-менеджер", "Бизнес и управление",
         "Управление продуктом, анализ пользователей и координация разработки новых функций.",
         "аналитика,пользователи,стратегия,коммуникации", "ВУЗ/Опыт", "100000-250000",
         "продукт,аналитика,стратегия,управление", "https://www.productplan.com/,https://amplitude.com/"),
        
        ("Преподаватель", "Наука и образование",
         "Обучение студентов, разработка учебных программ и проведение научных исследований.",
         "педагогика,предметные знания,исследования,коммуникации", "ВУЗ", "40000-120000",
         "образование,преподавание,наука,развитие", "https://www.edx.org/,https://coursera.org/"),
        
        ("Научный сотрудник", "Наука и образование",
         "Проведение научных исследований, публикация статей и участие в конференциях.",
         "исследования,анализ,публикации,статистика", "ВУЗ/Аспирантура", "50000-150000",
         "наука,исследования,анализ,публикации", "https://www.nature.com/,https://scholar.google.com/"),
        
        ("Переводчик", "Наука и образование",
         "Перевод текстов, документов и устная интерпретация между разными языками.",
         "иностранные языки,лингвистика,культура,коммуникации", "ВУЗ/Курсы", "50000-150000",
         "языки,перевод,лингвистика,культура", "https://www.deepl.com/,https://translate.google.com/"),
        
        ("Врач", "Медицина и здоровье",
         "Диагностика и лечение заболеваний, консультации пациентов и медицинские процедуры.",
         "медицина,диагностика,лечение,коммуникации", "ВУЗ/Ординатура", "80000-300000",
         "медицина,здоровье,лечение,помощь людям", "https://www.who.int/,https://www.cdc.gov/"),
        
        ("Психолог", "Медицина и здоровье",
         "Психологическая помощь, консультирование и проведение психологических тестов.",
         "психология,консультирование,тестирование,эмпатия", "ВУЗ", "60000-150000",
         "психология,помощь,консультирование,здоровье", "https://www.apa.org/,https://www.psychology.org/"),
        
        ("Фитнес-тренер", "Медицина и здоровье",
         "Проведение тренировок, составление программ питания и мотивация клиентов.",
         "фитнес,анатомия,питание,мотивация,коммуникации", "Курсы/Сертификаты", "40000-120000",
         "фитнес,здоровье,спорт,мотивация", "https://www.acefitness.org/,https://www.nasm.org/"),
        
        ("Медсестра", "Медицина и здоровье",
         "Уход за пациентами, выполнение медицинских процедур и помощь врачам.",
         "медицина,уход,процедуры,коммуникации,эмпатия", "Колледж/ВУЗ", "40000-100000",
         "медицина,уход,помощь,здоровье", "https://www.nursingworld.org/,https://www.icn.ch/"),
        
        ("Электрик", "Рабочие специальности",
         "Монтаж и обслуживание электрических систем, ремонт электрооборудования.",
         "электрика,монтаж,ремонт,безопасность,инструменты", "Колледж/Курсы", "50000-120000",
         "электрика,ремонт,монтаж,техника", "https://www.electricalsafetyfirst.org.uk/,https://www.nfpa.org/"),
        
        ("Сантехник", "Рабочие специальности",
         "Установка и ремонт сантехнического оборудования, водопроводных и канализационных систем.",
         "сантехника,монтаж,ремонт,инструменты,материалы", "Курсы/Опыт", "45000-110000",
         "сантехника,ремонт,монтаж,техника", "https://www.phccweb.org/,https://www.iapmo.org/"),
        
        ("Автомеханик", "Рабочие специальности",
         "Диагностика и ремонт автомобилей, обслуживание двигателей и электронных систем.",
         "автомобили,диагностика,ремонт,инструменты,электроника", "Колледж/Курсы", "50000-130000",
         "автомобили,ремонт,диагностика,техника", "https://www.ase.com/,https://www.sae.org/"),
        
        ("Строитель", "Рабочие специальности",
         "Строительство зданий, работа с различными материалами и строительными инструментами.",
         "строительство,материалы,инструменты,чертежи,безопасность", "Курсы/Опыт", "40000-100000",
         "строительство,ремонт,монтаж,техника", "https://www.osha.gov/,https://www.construction.com/"),
        
        ("Повар", "Сфера услуг",
         "Приготовление блюд, разработка меню и управление кухней в ресторанах.",
         "кулинария,меню,управление,творчество,гигиена", "Колледж/Курсы", "40000-100000",
         "кулинария,творчество,сервис,еда", "https://www.culinaryinstitute.edu/,https://www.chefsteps.com/"),
        
        ("Парикмахер", "Сфера услуг",
         "Стрижка, окрашивание и укладка волос, консультирование клиентов по уходу.",
         "парикмахерское дело,стилистика,химия,коммуникации", "Курсы/Лицензия", "35000-90000",
         "красота,стиль,творчество,сервис", "https://www.beauty-schools.com/,https://www.loreal.com/"),
        
        ("Турагент", "Сфера услуг",
         "Организация туристических поездок, консультирование клиентов и бронирование услуг.",
         "туризм,география,языки,коммуникации,продажи", "Курсы/Опыт", "30000-80000",
         "туризм,путешествия,сервис,география", "https://www.travelagentcentral.com/,https://www.booking.com/"),
        
        ("Консультант по продажам", "Сфера услуг",
         "Консультирование клиентов, презентация товаров и услуг, работа с возражениями.",
         "продажи,коммуникации,психология,продукты,переговоры", "Опыт/Курсы", "40000-120000",
         "продажи,консультирование,коммуникации,сервис", "https://www.salesforce.com/,https://www.hubspot.com/"),
        
        ("Логист", "Сфера услуг",
         "Организация перевозок, управление складскими запасами и оптимизация цепочек поставок.",
         "логистика,склад,транспорт,планирование,аналитика", "ВУЗ/Курсы", "50000-130000",
         "логистика,транспорт,склад,планирование", "https://www.cscmp.org/,https://www.supplychain247.com/"),
        
        ("Мобильный разработчик", "IT и технологии",
         "Разработка мобильных приложений для iOS и Android платформ.",
         "Swift,Kotlin,React Native,Flutter,мобильная разработка", "ВУЗ/Курсы", "90000-220000",
         "мобильные приложения,программирование,ios,android", "https://developer.apple.com/,https://developer.android.com/"),
        
        ("Кибербезопасность", "IT и технологии",
         "Защита информационных систем от кибератак и обеспечение безопасности данных.",
         "безопасность,сети,криптография,анализ угроз,мониторинг", "ВУЗ/Сертификаты", "100000-250000",
         "безопасность,хакерство,защита,анализ", "https://www.cisecurity.org/,https://www.sans.org/"),
        
        ("Game Developer", "IT и технологии",
         "Разработка компьютерных игр, создание игровых механик и программирование игрового движка.",
         "Unity,Unreal Engine,C#,C++,игровой дизайн,3D моделирование", "ВУЗ/Курсы", "80000-200000",
         "игры,программирование,творчество,3D", "https://unity.com/,https://www.unrealengine.com/"),
        
        ("Blockchain разработчик", "IT и технологии",
         "Разработка децентрализованных приложений и смарт-контрактов на блокчейн платформах.",
         "Solidity,Web3,JavaScript,криптография,смарт-контракты", "ВУЗ/Курсы", "120000-300000",
         "блокчейн,криптовалюты,децентрализация,программирование", "https://ethereum.org/,https://docs.soliditylang.org/"),
        
        ("Фотограф", "Творчество и дизайн",
         "Создание фотографий для различных целей: портреты, свадьбы, коммерческая съемка.",
         "фотография,композиция,свет,постобработка,Photoshop", "Курсы/Портфолио", "40000-150000",
         "фотография,творчество,искусство,визуал", "https://www.adobe.com/,https://www.photography.com/"),
        
        ("Иллюстратор", "Творчество и дизайн",
         "Создание иллюстраций для книг, журналов, рекламы и цифровых продуктов.",
         "рисование,Photoshop,Illustrator,стили,композиция", "Курсы/Портфолио", "50000-140000",
         "иллюстрация,рисование,творчество,искусство", "https://www.adobe.com/,https://www.behance.net/"),
        
        ("Архитектор", "Творчество и дизайн",
         "Проектирование зданий и сооружений, создание архитектурных чертежей и 3D моделей.",
         "AutoCAD,SketchUp,3D моделирование,строительство,дизайн", "ВУЗ", "80000-200000",
         "архитектура,дизайн,строительство,творчество", "https://www.autodesk.com/,https://www.sketchup.com/"),
        
        ("Финансовый аналитик", "Бизнес и управление",
         "Анализ финансовых данных, оценка инвестиций и подготовка финансовых отчетов.",
         "финансы,Excel,аналитика,моделирование,статистика", "ВУЗ", "80000-200000",
         "финансы,аналитика,инвестиции,отчеты", "https://www.cfainstitute.org/,https://www.bloomberg.com/"),
        
        ("Консультант", "Бизнес и управление",
         "Консультирование компаний по различным вопросам: стратегия, операции, технологии.",
         "консультирование,аналитика,стратегия,коммуникации", "ВУЗ/Опыт", "100000-300000",
         "консультирование,стратегия,аналитика,бизнес", "https://www.mckinsey.com/,https://www.bcg.com/"),
        
        ("Event-менеджер", "Бизнес и управление",
         "Организация мероприятий: корпоративы, конференции, свадьбы и другие события.",
         "планирование,координация,творчество,коммуникации,бюджет", "Курсы/Опыт", "50000-130000",
         "мероприятия,планирование,творчество,координация", "https://www.eventbrite.com/,https://www.cvent.com/"),
        
        ("Стилист", "Сфера услуг",
         "Создание образов, подбор одежды и аксессуаров, консультирование по стилю.",
         "стилистика,мода,цвет,композиция,коммуникации", "Курсы/Опыт", "40000-120000",
         "стиль,мода,красота,творчество", "https://www.vogue.com/,https://www.style.com/"),
        
        ("Коуч", "Сфера услуг",
         "Помощь людям в достижении целей, развитие навыков и личностный рост.",
         "коучинг,психология,мотивация,коммуникации,развитие", "Курсы/Сертификаты", "60000-150000",
         "коучинг,развитие,мотивация,психология", "https://www.icf.org/,https://www.coachfederation.org/"),
        
        ("Няня", "Сфера услуг",
         "Уход за детьми, организация досуга и помощь в развитии ребенка.",
         "педагогика,психология,творчество,ответственность,терпение", "Курсы/Опыт", "30000-80000",
         "дети,уход,воспитание,развитие", "https://www.care.com/,https://www.sittercity.com/"),
        
        ("Инженер-конструктор", "Рабочие специальности",
         "Проектирование технических изделий, создание чертежей и технической документации.",
         "CAD,инженерия,чертежи,материалы,расчеты", "ВУЗ", "70000-180000",
         "инженерия,проектирование,техника,чертежи", "https://www.autodesk.com/,https://www.solidworks.com/"),
        
        ("Технолог", "Рабочие специальности",
         "Разработка технологических процессов производства и контроль качества продукции.",
         "технологии,производство,качество,анализ,оптимизация", "ВУЗ", "60000-150000",
         "технологии,производство,качество,оптимизация", "https://www.astm.org/,https://www.iso.org/"),
        
        ("Сварщик", "Рабочие специальности",
         "Соединение металлических деталей с помощью различных видов сварки.",
         "сварка,металлы,инструменты,безопасность,чертежи", "Курсы/Сертификаты", "50000-120000",
         "сварка,металлы,производство,техника", "https://www.aws.org/,https://www.lincolnelectric.com/"),
        
        ("Библиотекарь", "Наука и образование",
         "Организация библиотечных фондов, помощь читателям и проведение культурных мероприятий.",
         "каталогизация,информационные технологии,коммуникации,культура", "ВУЗ/Курсы", "30000-70000",
         "книги,информация,культура,образование", "https://www.ala.org/,https://www.ifla.org/"),
        
        ("Лаборант", "Наука и образование",
         "Проведение лабораторных исследований, анализ образцов и ведение документации.",
         "лабораторное оборудование,химия,биология,анализ,документация", "Колледж/ВУЗ", "40000-90000",
         "лаборатория,исследования,анализ,наука", "https://www.labmanager.com/,https://www.sigmaaldrich.com/"),
        
        ("Эколог", "Наука и образование",
         "Исследование окружающей среды, оценка экологических рисков и разработка природоохранных мер.",
         "экология,биология,химия,анализ,мониторинг", "ВУЗ", "50000-120000",
         "экология,природа,исследования,охрана", "https://www.epa.gov/,https://www.unep.org/"),
        
        ("Фармацевт", "Медицина и здоровье",
         "Изготовление и отпуск лекарств, консультирование по применению медикаментов.",
         "фармакология,химия,медицина,консультирование", "ВУЗ", "60000-140000",
         "фармакология,лекарства,здоровье,консультирование", "https://www.fda.gov/,https://www.who.int/"),
        
        ("Массажист", "Медицина и здоровье",
         "Проведение лечебного и расслабляющего массажа, помощь в восстановлении здоровья.",
         "анатомия,массаж,физиология,коммуникации,эмпатия", "Курсы/Лицензия", "40000-100000",
         "массаж,здоровье,релаксация,медицина", "https://www.amtamassage.org/,https://www.ncbtmb.org/"),
        
        ("Диетолог", "Медицина и здоровье",
         "Консультирование по правильному питанию, составление диет и планов питания.",
         "диетология,питание,биохимия,консультирование,анализ", "ВУЗ", "50000-120000",
         "питание,диетология,здоровье,консультирование", "https://www.eatright.org/,https://www.nutrition.org/")
    ]
    
    for career in careers_data:
        c.execute("""
        INSERT INTO careers(name, category, description, skills_required, education_level, 
                          salary_range, tags, learning_resources, created_at)
        VALUES(?,?,?,?,?,?,?,?,?)
        """, (*career, datetime.utcnow().isoformat()))
    
    conn.commit()
    conn.close()
    print(f"Added {len(careers_data)} careers to database")

def seed_test_questions():
    """Заполнение базы данных тестовыми вопросами"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM test_questions")
    if c.fetchone()[0] > 0:
        conn.close()
        return
    
    questions_data = [
        ("Что тебя больше всего привлекает в работе?", 
         "Создание чего-то нового,Решение сложных задач,Помощь людям,Анализ данных,Управление процессами,Работа с техникой",
         "CREATIVE:3,IT:2,BUSINESS:1,SCIENCE:2,MEDICAL:3,TECHNICAL:1",
         "general", 1),
        
        ("Какой тип задач тебе нравится больше всего?",
         "Программирование и разработка,Дизайн и творчество,Планирование и организация,Исследования и анализ,Лечение и помощь,Работа руками",
         "IT:4,CREATIVE:3,BUSINESS:2,SCIENCE:3,MEDICAL:2,TECHNICAL:3",
         "tasks", 2),
        
        ("В какой среде ты предпочитаешь работать?",
         "За компьютером в офисе,В творческой студии,В переговорных комнатах,В лаборатории,В больнице/клинике,На производстве",
         "IT:4,CREATIVE:4,BUSINESS:3,SCIENCE:4,MEDICAL:4,TECHNICAL:3",
         "environment", 3),
        
        ("Что для тебя важнее в карьере?",
         "Высокая зарплата,Творческая самореализация,Карьерный рост,Научные открытия,Помощь людям,Стабильность",
         "IT:2,CREATIVE:4,BUSINESS:3,SCIENCE:3,MEDICAL:4,TECHNICAL:2",
         "values", 4),
        
        ("Как ты предпочитаешь учиться?",
         "Онлайн курсы и практика,Художественные мастер-классы,Бизнес-тренинги,Научные исследования,Медицинская практика,Работа с инструментами",
         "IT:4,CREATIVE:3,BUSINESS:2,SCIENCE:3,MEDICAL:3,TECHNICAL:3",
         "learning", 5),
        
        ("Какой уровень ответственности тебя привлекает?",
         "Высокий - управление проектами,Средний - работа в команде,Высокий - принятие решений,Средний - исследовательская работа,Высокий - жизнь людей,Средний - качество работы",
         "IT:2,BUSINESS:4,SCIENCE:2,MEDICAL:4,TECHNICAL:2",
         "responsibility", 6),
        
        ("Что тебя мотивирует больше всего?",
         "Технологические инновации,Красота и эстетика,Достижение целей,Научные открытия,Здоровье людей,Качественный результат",
         "IT:4,CREATIVE:4,BUSINESS:3,SCIENCE:4,MEDICAL:4,TECHNICAL:3",
         "motivation", 7),
        
        ("Как ты относишься к рутинной работе?",
         "Терпеть не могу,Иногда нормально,Принимаю как необходимость,Могу работать с данными,Важна для здоровья,Это основа качества",
         "IT:1,CREATIVE:1,BUSINESS:2,SCIENCE:2,MEDICAL:2,TECHNICAL:3",
         "routine", 8),
        
        ("Какой тип коммуникации тебе ближе?",
         "С коллегами-разработчиками,С клиентами и творческими людьми,С командой и партнерами,С научным сообществом,С пациентами,С заказчиками",
         "IT:3,CREATIVE:3,BUSINESS:4,SCIENCE:3,MEDICAL:4,TECHNICAL:2",
         "communication", 9),
        
        ("Что для тебя означает успех в карьере?",
         "Создание популярного продукта,Признание в творческой среде,Рост компании,Научные публикации,Спасенные жизни,Надежные системы",
         "IT:4,CREATIVE:4,BUSINESS:3,SCIENCE:4,MEDICAL:4,TECHNICAL:3",
         "success", 10),
        
        ("Как ты предпочитаешь решать проблемы?",
         "Через код и алгоритмы,Творческим подходом,Через планирование,Через анализ данных,Через диагностику,Через практические методы",
         "IT:4,CREATIVE:3,BUSINESS:2,SCIENCE:3,MEDICAL:3,TECHNICAL:3",
         "problem_solving", 11),

        ("Какой график работы тебе подходит?",
         "Гибкий, с возможностью удаленки,Свободный творческий,Стандартный офисный,Лабораторный с исследованиями,Дежурства и смены,Производственный",
         "IT:4,CREATIVE:3,BUSINESS:2,SCIENCE:2,MEDICAL:1,TECHNICAL:2",
         "schedule", 12),

        ("Что тебя больше всего интересует?",
         "Новые технологии,Искусство и дизайн,Бизнес-процессы,Научные явления,Человеческое здоровье,Технические системы",
         "IT:4,CREATIVE:4,BUSINESS:3,SCIENCE:4,MEDICAL:4,TECHNICAL:4",
         "interests", 13),

        ("Как ты относишься к работе в команде?",
         "Предпочитаю небольшие команды,Люблю творческие коллаборации,Отлично работаю в команде,Работаю в исследовательских группах,Командная работа в медицине,Работаю с бригадой",
         "IT:3,CREATIVE:3,BUSINESS:4,SCIENCE:3,MEDICAL:4,TECHNICAL:3",
         "teamwork", 14),

        ("Что для тебя важнее в работе?",
         "Инновации и технологии,Красота и эстетика,Эффективность и результат,Точность и анализ,Здоровье и безопасность,Надежность и качество",
         "IT:4,CREATIVE:4,BUSINESS:3,SCIENCE:3,MEDICAL:4,TECHNICAL:4",
         "priorities", 15)
    ]
    
    for question in questions_data:
        c.execute("""
        INSERT INTO test_questions(question_text, options, weights, category, order_num)
        VALUES(?,?,?,?,?)
        """, question)
    
    conn.commit()
    conn.close()
    print(f"Added {len(questions_data)} test questions to database")

def get_user_profile(user_id: int) -> Optional[Dict]:
    """Получить профиль пользователя"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    SELECT user_id, first_name, username, age_group, education, 
           interests, skills, current_job, satisfaction, created_at, updated_at
    FROM users WHERE user_id = ?
    """, (user_id,))
    
    row = c.fetchone()
    conn.close()
    
    if row:
        return {
            "user_id": row[0],
            "first_name": row[1],
            "username": row[2],
            "age_group": row[3],
            "education": row[4],
            "interests": row[5],
            "skills": row[6],
            "current_job": row[7],
            "satisfaction": row[8],
            "created_at": row[9],
            "updated_at": row[10]
        }
    return None

def save_user_profile(user_id: int, first_name: str, username: str, profile: Dict):
    """Сохранить профиль пользователя"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    
    c.execute("""
    INSERT INTO users(user_id, first_name, username, age_group, education, 
                     interests, skills, current_job, satisfaction, created_at, updated_at)
    VALUES(?,?,?,?,?,?,?,?,?,?,?)
    ON CONFLICT(user_id) DO UPDATE SET
      first_name=excluded.first_name,
      username=excluded.username,
      age_group=excluded.age_group,
      education=excluded.education,
      interests=excluded.interests,
      skills=excluded.skills,
      current_job=excluded.current_job,
      satisfaction=excluded.satisfaction,
      updated_at=excluded.updated_at
    """, (user_id, first_name, username, 
          profile.get("age_group"), profile.get("education"),
          profile.get("interests"), profile.get("skills"),
          profile.get("current_job"), profile.get("satisfaction"),
          now, now))
    
    conn.commit()
    conn.close()

def record_interaction(user_id: int, action: str, details: str = ""):
    """Записать взаимодействие пользователя"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    INSERT INTO interactions(user_id, action, details, timestamp)
    VALUES(?,?,?,?)
    """, (user_id, action, details, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

async def cleanup_old_messages(context: ContextTypes.DEFAULT_TYPE, user_id: int, keep_last: int = 2):
    """Удалить старые сообщения бота для пользователя"""
    try:
        if 'bot_messages' not in context.bot_data:
            context.bot_data['bot_messages'] = {}
        
        if user_id not in context.bot_data['bot_messages']:
            context.bot_data['bot_messages'][user_id] = []
        
        messages = context.bot_data['bot_messages'][user_id]
        
        while len(messages) > keep_last:
            old_message_id = messages.pop(0)
            try:
                await context.bot.delete_message(chat_id=user_id, message_id=old_message_id)
            except:
                pass
                
    except Exception as e:
        print(f"Ошибка при очистке сообщений: {e}")

async def track_message(context: ContextTypes.DEFAULT_TYPE, user_id: int, message_id: int):
    """Отслеживать сообщения бота для последующего удаления"""
    try:
        if 'bot_messages' not in context.bot_data:
            context.bot_data['bot_messages'] = {}
        
        if user_id not in context.bot_data['bot_messages']:
            context.bot_data['bot_messages'][user_id] = []
        
        context.bot_data['bot_messages'][user_id].append(message_id)
    except Exception as e:
        print(f"Ошибка при отслеживании сообщения: {e}")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - приветствие и главное меню"""
    user = update.effective_user
    record_interaction(user.id, "start_command")

    profile = get_user_profile(user.id)
    
    welcome_text = f"👋 Привет, {user.first_name}!\n\n"
    welcome_text += "🎯 Я помогу тебе найти идеальную профессию!\n"
    welcome_text += "Проходи тесты, изучай варианты карьеры и получай персональные рекомендации.\n\n"
    
    if not profile:
        welcome_text += "📝 Для начала давай создадим твой профиль!"
    
    keyboard = [
        [InlineKeyboardButton("👤 Мой профиль", callback_data="profile")],
        [InlineKeyboardButton("🧠 Пройти тест", callback_data="test")],
        [InlineKeyboardButton("💡 Рекомендации", callback_data="recommendations")],
        [InlineKeyboardButton("🔍 Поиск профессий", callback_data="search")],
        [InlineKeyboardButton("💼 Актуальные вакансии", callback_data="vacancies")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    sent_message = await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    await track_message(context, user.id, sent_message.message_id)

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /profile - просмотр профиля"""
    user = update.effective_user
    record_interaction(user.id, "profile_command")
    
    profile = get_user_profile(user.id)
    
    if not profile:
        await update.message.reply_text(
            "📝 У тебя пока нет профиля. Давай создадим его!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Создать профиль", callback_data="create_profile")
            ]])
        )
        return
    
    profile_text = f"👤 Твой профиль:\n\n"
    profile_text += f"👶 Возрастная группа: {profile.get('age_group', 'Не указано')}\n"
    profile_text += f"🎓 Образование: {profile.get('education', 'Не указано')}\n"
    profile_text += f"❤️ Интересы: {profile.get('interests', 'Не указано')}\n"
    profile_text += f"🛠️ Навыки: {profile.get('skills', 'Не указано')}\n"
    profile_text += f"💼 Текущая работа: {profile.get('current_job', 'Не указано')}\n"
    profile_text += f"😊 Удовлетворенность: {profile.get('satisfaction', 'Не указано')}/5"
    
    keyboard = [
        [InlineKeyboardButton("✏️ Редактировать", callback_data="edit_profile")],
        [InlineKeyboardButton("🗑️ Удалить профиль", callback_data="delete_profile")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    
    await update.message.reply_text(
        profile_text, 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /test - начать карьерный тест"""
    user = update.effective_user
    record_interaction(user.id, "test_command")
    
    profile = get_user_profile(user.id)
    if not profile:
        await update.message.reply_text(
            "📝 Сначала создай профиль, чтобы получить более точные рекомендации!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Создать профиль", callback_data="create_profile")
            ]])
        )
        return
    
    await update.message.reply_text(
        "🧠 Отлично! Давай пройдем карьерный тест.\n\n"
        "Я задам тебе несколько вопросов, чтобы понять, какие профессии тебе подходят.\n"
        "Готов начать?",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Начать тест", callback_data="start_test")
        ]])
    )

def generate_recommendations(user_id: int, top_k: int = 5) -> List[Dict]:
    """Генерация рекомендаций на основе профиля и тестов"""
    profile = get_user_profile(user_id)
    test_results = get_user_test_results(user_id)
    all_careers = get_careers_by_category()
    
    if not profile:
        return []
    
    interests = set([i.strip().lower() for i in (profile.get("interests") or "").split(",") if i.strip()])
    skills = set([s.strip().lower() for s in (profile.get("skills") or "").split(",") if s.strip()])
    education = profile.get("education", "").lower()
    satisfaction = profile.get("satisfaction", 3)
    
    career_scores = []
    
    for career in all_careers:
        score = 0
        
        career_tags = set([t.lower() for t in career["tags"] if t])
        interest_matches = len(interests & career_tags)
        score += interest_matches * 3
        
        career_skills = set([s.lower() for s in career["skills_required"] if s])
        skill_matches = len(skills & career_skills)
        score += skill_matches * 4
    
        if education and education in (career["education_level"] or "").lower():
            score += 2

        if test_results:
            career_category = career["category"]

            category_mapping = {
                "IT и технологии": "IT",
                "Творчество и дизайн": "CREATIVE", 
                "Бизнес и управление": "BUSINESS",
                "Наука и образование": "SCIENCE",
                "Медицина и здоровье": "MEDICAL",
                "Рабочие специальности": "TECHNICAL",
                "Сфера услуг": "SERVICE"
            }
            
            mapped_category = category_mapping.get(career_category)
            if mapped_category and mapped_category in test_results:
                score += test_results[mapped_category] * 5

        if satisfaction <= 2:
            if "creative" in career_tags or "product" in career_tags or "design" in career_tags:
                score += 2
        
        career_scores.append((score, career))
    
    career_scores.sort(key=lambda x: x[0], reverse=True)

    return [career for score, career in career_scores[:top_k] if score > 0]

async def recommendations_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /recommendations - получить рекомендации"""
    user = update.effective_user
    record_interaction(user.id, "recommendations_command")
    
    profile = get_user_profile(user.id)
    if not profile:
        await update.message.reply_text(
            "📝 Сначала создай профиль, чтобы получить рекомендации!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Создать профиль", callback_data="create_profile")
            ]])
        )
        return

    recommendations = generate_recommendations(user.id, top_k=5)
    
    if not recommendations:
        await update.message.reply_text(
            "😔 Пока не могу найти подходящие профессии.\n\n"
            "Попробуй:\n"
            "• Пройти карьерный тест (/test)\n"
            "• Добавить больше интересов и навыков в профиль\n"
            "• Использовать поиск профессий (/search)",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🧠 Пройти тест", callback_data="test"),
                InlineKeyboardButton("🔍 Поиск", callback_data="search")
            ]])
        )
        return

    text = "💡 Твои персональные рекомендации:\n\n"
    
    for i, career in enumerate(recommendations, 1):
        text += f"{i}. {career['name']}\n"
        text += f"📂 {career['category']}\n"
        text += f"💰 {career['salary_range']} руб/мес\n"
        text += f"📝 {career['description'][:100]}...\n"
        
        if career['skills_required']:
            skills_text = ", ".join(career['skills_required'][:3])
            text += f"🛠️ Навыки: {skills_text}\n"
        
        text += f"🎓 {career['education_level']}\n\n"
    
    text += "💡 Хочешь узнать больше о какой-то профессии? Используй /search"
    
    keyboard = [
        [InlineKeyboardButton("🧠 Пройти тест", callback_data="test")],
        [InlineKeyboardButton("🔍 Поиск профессий", callback_data="search")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    
    await update.message.reply_text(
        text, 
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /search - поиск профессий"""
    user = update.effective_user
    record_interaction(user.id, "search_command")
    
    await update.message.reply_text(
        "🔍 Поиск профессий\n\n"
        "Введи ключевые слова для поиска (например: 'программист', 'дизайн', 'медицина'):"
    )
    
    return SEARCH_QUERY

async def vacancies_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /vacancies - актуальные вакансии"""
    user = update.effective_user
    record_interaction(user.id, "vacancies_command")
    
    await update.message.reply_text(
        "💼 Актуальные вакансии\n\n"
        "Введи название профессии для поиска вакансий на HH.ru:"
    )
    
    return SEARCH_QUERY

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на inline-кнопки"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "main_menu":
        await handle_main_menu_callback(query, context)
    elif data == "profile":
        await handle_profile_callback(query, context)
    elif data == "test":
        await handle_test_callback(query, context)
    elif data == "recommendations":
        await handle_recommendations_callback(query, context)
    elif data == "search":
        await handle_search_callback(query, context)
    elif data == "vacancies":
        await handle_vacancies_callback(query, context)
    elif data == "create_profile":
        await start_profile_creation(query, context)
    elif data == "edit_profile":
        await start_profile_editing(query, context)
    elif data == "start_test":
        await start_career_test(query, context)
    elif data.startswith("age_"):
        await handle_age_selection(query, context, data)
    elif data == "skip_age":
        await handle_skip_age(query, context)
    elif data.startswith("edu_"):
        await handle_education_selection(query, context, data)
    elif data == "skip_education":
        await handle_skip_education(query, context)
    elif data == "save_interests":
        await handle_save_interests(query, context)
    elif data == "skip_interests":
        await handle_skip_interests(query, context)
    elif data == "save_skills":
        await handle_save_skills(query, context)
    elif data == "skip_skills":
        await handle_skip_skills(query, context)
    elif data == "save_current_job":
        await handle_save_current_job(query, context)
    elif data == "skip_current_job":
        await handle_skip_current_job(query, context)
    elif data.startswith("satisfaction_"):
        await handle_satisfaction_selection(query, context, data)
    elif data == "skip_satisfaction":
        await handle_skip_satisfaction(query, context)
    elif data == "complete_profile":
        await handle_complete_profile(query, context)
    elif data.startswith("test_answer_"):
        await handle_test_answer(query, context, data)
    elif data == "finish_test":
        await handle_finish_test(query, context)
    elif data == "edit_age":
        await handle_edit_age(query, context)
    elif data == "edit_education":
        await handle_edit_education(query, context)
    elif data == "edit_interests":
        await handle_edit_interests(query, context)
    elif data == "edit_skills":
        await handle_edit_skills(query, context)
    elif data == "edit_current_job":
        await handle_edit_current_job(query, context)
    elif data == "edit_satisfaction":
        await handle_edit_satisfaction(query, context)
    elif data == "delete_profile":
        await handle_delete_profile(query, context)
    elif data == "confirm_delete":
        await handle_confirm_delete(query, context)
    elif data == "cancel_delete":
        await handle_cancel_delete(query, context)
    else:
        await query.message.reply_text("❌ Неизвестная команда")

async def handle_main_menu_callback(query, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик главного меню"""
    user = query.from_user
    record_interaction(user.id, "main_menu_callback")
    
    welcome_text = f"👋 Привет, {user.first_name}!\n\n"
    welcome_text += "🎯 Я помогу тебе найти идеальную профессию!\n"
    welcome_text += "Проходи тесты, изучай варианты карьеры и получай персональные рекомендации.\n\n"
    
    keyboard = [
        [InlineKeyboardButton("👤 Мой профиль", callback_data="profile")],
        [InlineKeyboardButton("🧠 Пройти тест", callback_data="test")],
        [InlineKeyboardButton("💡 Рекомендации", callback_data="recommendations")],
        [InlineKeyboardButton("🔍 Поиск профессий", callback_data="search")],
        [InlineKeyboardButton("💼 Актуальные вакансии", callback_data="vacancies")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(welcome_text, reply_markup=reply_markup)

async def handle_profile_callback(query, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик профиля"""
    user = query.from_user
    record_interaction(user.id, "profile_callback")
    
    profile = get_user_profile(user.id)
    
    if not profile:
        await query.message.reply_text(
            "📝 У тебя пока нет профиля. Давай создадим его!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Создать профиль", callback_data="create_profile")
            ]])
        )
        return
    
    profile_text = f"👤 Твой профиль:\n\n"
    profile_text += f"👶 Возрастная группа: {profile.get('age_group', 'Не указано')}\n"
    profile_text += f"🎓 Образование: {profile.get('education', 'Не указано')}\n"
    profile_text += f"❤️ Интересы: {profile.get('interests', 'Не указано')}\n"
    profile_text += f"🛠️ Навыки: {profile.get('skills', 'Не указано')}\n"
    profile_text += f"💼 Текущая работа: {profile.get('current_job', 'Не указано')}\n"
    profile_text += f"😊 Удовлетворенность: {profile.get('satisfaction', 'Не указано')}/5"
    
    keyboard = [
        [InlineKeyboardButton("✏️ Редактировать", callback_data="edit_profile")],
        [InlineKeyboardButton("🗑️ Удалить профиль", callback_data="delete_profile")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    
    await query.message.reply_text(
        profile_text, 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_test_callback(query, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик теста"""
    user = query.from_user
    record_interaction(user.id, "test_callback")
    
    profile = get_user_profile(user.id)
    if not profile:
        await query.message.reply_text(
            "📝 Сначала создай профиль, чтобы получить более точные рекомендации!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Создать профиль", callback_data="create_profile")
            ]])
        )
        return
    
    await query.message.reply_text(
        "🧠 Отлично! Давай пройдем карьерный тест.\n\n"
        "Я задам тебе несколько вопросов, чтобы понять, какие профессии тебе подходят.\n"
        "Готов начать?",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Начать тест", callback_data="start_test")
        ]])
    )

async def handle_recommendations_callback(query, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик рекомендаций"""
    user = query.from_user
    record_interaction(user.id, "recommendations_callback")
    
    profile = get_user_profile(user.id)
    if not profile:
        await query.message.reply_text(
            "📝 Сначала создай профиль, чтобы получить рекомендации!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Создать профиль", callback_data="create_profile")
            ]])
        )
        return
    
    loading_msg = await query.message.reply_text("🔄 Анализируем твой профиль...")
    await asyncio.sleep(1)
    
    await loading_msg.edit_text("🧠 Изучаем твои интересы и навыки...")
    await asyncio.sleep(1)
    
    await loading_msg.edit_text("📊 Сравниваем с базой профессий...")
    await asyncio.sleep(1)
    
    await loading_msg.edit_text("💡 Генерируем персональные рекомендации...")
    await asyncio.sleep(1)
    
    recommendations = generate_recommendations(user.id, top_k=5)
    
    if not recommendations:
        await loading_msg.edit_text(
            "😔 Пока не могу найти подходящие профессии.\n\n"
            "Попробуй:\n"
            "• Пройти карьерный тест (/test)\n"
            "• Добавить больше интересов и навыков в профиль\n"
            "• Использовать поиск профессий (/search)",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🧠 Пройти тест", callback_data="test"),
                InlineKeyboardButton("🔍 Поиск", callback_data="search")
            ]])
        )
        return
    
    await loading_msg.edit_text("✨ Рекомендации готовы!")
    await asyncio.sleep(1)
    
    text = "🎯 Твои персональные рекомендации:\n\n"
    
    for i, career in enumerate(recommendations, 1):
        category_emoji = {
            "IT и технологии": "💻",
            "Творчество и дизайн": "🎨",
            "Бизнес и управление": "💼",
            "Наука и образование": "🔬",
            "Медицина и здоровье": "🏥",
            "Рабочие специальности": "🔧",
            "Сфера услуг": "🤝"
        }
        
        emoji = category_emoji.get(career['category'], "📈")
        
        text += f"{emoji} {i}. {career['name']}\n"
        text += f"📂 {career['category']}\n"
        text += f"💰 {career['salary_range']} руб/мес\n"
        text += f"📝 {career['description'][:100]}...\n"
        
        if career['skills_required']:
            skills_text = ", ".join(career['skills_required'][:3])
            text += f"🛠️ Навыки: {skills_text}\n"
        
        text += f"🎓 {career['education_level']}\n\n"
    
    text += "💡 Хочешь узнать больше о какой-то профессии? Используй поиск!"
    
    keyboard = [
        [InlineKeyboardButton("🧠 Пройти тест", callback_data="test")],
        [InlineKeyboardButton("🔍 Поиск профессий", callback_data="search")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    
    await loading_msg.edit_text(
        text, 
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_search_callback(query, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик поиска"""
    user = query.from_user
    record_interaction(user.id, "search_callback")
    
    await query.message.reply_text(
        "🔍 Поиск профессий\n\n"
        "Введи ключевые слова для поиска (например: 'программист', 'дизайн', 'медицина'):"
    )

    context.user_data['waiting_for_search'] = True

async def handle_vacancies_callback(query, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик вакансий"""
    user = query.from_user
    record_interaction(user.id, "vacancies_callback")
    
    context.user_data['search_platform'] = 'hh'
    context.user_data['waiting_for_vacancy_search'] = True
    
    await query.message.reply_text(
        "💼 Поиск актуальных вакансий на HH.ru\n\n"
        "Введи название профессии для поиска вакансий:",
        parse_mode="Markdown"
    )

async def start_profile_creation(query, context: ContextTypes.DEFAULT_TYPE):
    """Начать создание профиля"""
    user = query.from_user
    record_interaction(user.id, "start_profile_creation")
    
    context.user_data['profile'] = {
        'user_id': user.id,
        'first_name': user.first_name,
        'username': user.username
    }
    
    loading_msg = await query.message.reply_text("🔄 Создаем твой профиль...")
    await asyncio.sleep(1)
    
    await loading_msg.edit_text("✨ Отлично! Давай создадим твой персональный профиль!")
    await asyncio.sleep(1)
    
    await loading_msg.edit_text(
        "👶 Шаг 1/6: Возрастная группа\n\n"
        "Выбери свою возрастную группу:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("13-17 лет", callback_data="age_13_17")],
            [InlineKeyboardButton("18-24 года", callback_data="age_18_24")],
            [InlineKeyboardButton("25-35 лет", callback_data="age_25_35")],
            [InlineKeyboardButton("36+ лет", callback_data="age_36_plus")],
            [InlineKeyboardButton("❌ Пропустить", callback_data="skip_age")]
        ])
    )

async def start_profile_editing(query, context: ContextTypes.DEFAULT_TYPE):
    """Начать редактирование профиля"""
    user = query.from_user
    record_interaction(user.id, "start_profile_editing")
    
    profile = get_user_profile(user.id)
    if not profile:
        await query.message.reply_text(
            "📝 У тебя пока нет профиля для редактирования!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Создать профиль", callback_data="create_profile")
            ]])
        )
        return
    
    profile_text = "✏️ Редактирование профиля\n\n"
    profile_text += f"👶 Возрастная группа: {profile.get('age_group', 'Не указано')}\n"
    profile_text += f"🎓 Образование: {profile.get('education', 'Не указано')}\n"
    profile_text += f"❤️ Интересы: {profile.get('interests', 'Не указано')}\n"
    profile_text += f"🛠️ Навыки: {profile.get('skills', 'Не указано')}\n"
    profile_text += f"💼 Текущая работа: {profile.get('current_job', 'Не указано')}\n"
    profile_text += f"😊 Удовлетворенность: {profile.get('satisfaction', 'Не указано')}/5\n\n"
    profile_text += "Выбери, что хочешь изменить:"
    
    keyboard = [
        [InlineKeyboardButton("👶 Возрастная группа", callback_data="edit_age")],
        [InlineKeyboardButton("🎓 Образование", callback_data="edit_education")],
        [InlineKeyboardButton("❤️ Интересы", callback_data="edit_interests")],
        [InlineKeyboardButton("🛠️ Навыки", callback_data="edit_skills")],
        [InlineKeyboardButton("💼 Текущая работа", callback_data="edit_current_job")],
        [InlineKeyboardButton("😊 Удовлетворенность", callback_data="edit_satisfaction")],
        [InlineKeyboardButton("🗑️ Удалить профиль", callback_data="delete_profile")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    
    await query.message.reply_text(
        profile_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_age_selection(query, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Обработка выбора возрастной группы"""
    user = query.from_user
    record_interaction(user.id, "age_selection", data)
    
    age_mapping = {
        "age_13_17": "13-17 лет",
        "age_18_24": "18-24 года", 
        "age_25_35": "25-35 лет",
        "age_36_plus": "36+ лет"
    }
    
    if 'profile' in context.user_data:
        context.user_data['profile']['age_group'] = age_mapping[data]

        age_group = age_mapping[data]
        is_under_18 = age_group == "13-17 лет"
        
        if is_under_18:
            context.user_data['profile']['total_steps'] = 5 
        else:
            context.user_data['profile']['total_steps'] = 6

        await query.message.edit_text("✅ Возрастная группа сохранена!")
        await asyncio.sleep(1)
        
        step_num = 2
        total_steps = context.user_data['profile']['total_steps']
        await query.message.edit_text(
            f"🎓 Шаг {step_num}/{total_steps}: Образование\n\n"
            "Выбери свой уровень образования:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏫 Школа", callback_data="edu_school")],
                [InlineKeyboardButton("🎓 ВУЗ", callback_data="edu_university")],
                [InlineKeyboardButton("📚 Курсы", callback_data="edu_courses")],
                [InlineKeyboardButton("💼 Опыт работы", callback_data="edu_experience")],
                [InlineKeyboardButton("❌ Пропустить", callback_data="skip_education")]
            ])
        )
    else:
        profile = get_user_profile(user.id)
        if profile:
            profile['age_group'] = age_mapping[data]
            save_user_profile(user.id, user.first_name, user.username, profile)
            await query.message.edit_text("✅ Возрастная группа обновлена!")
            await asyncio.sleep(1)
            await query.message.edit_text(
                "✏️ Профиль обновлен!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✏️ Редактировать еще", callback_data="edit_profile"),
                    InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
                ]])
            )

async def handle_skip_age(query, context: ContextTypes.DEFAULT_TYPE):
    """Пропуск возрастной группы"""
    await handle_age_selection(query, context, "age_18_24")

async def handle_education_selection(query, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Обработка выбора образования"""
    user = query.from_user
    record_interaction(user.id, "education_selection", data)

    edu_mapping = {
        "edu_school": "Школа",
        "edu_university": "ВУЗ",
        "edu_courses": "Курсы", 
        "edu_experience": "Опыт работы"
    }

    if 'profile' in context.user_data:
        context.user_data['profile']['education'] = edu_mapping[data]
        
        await query.message.edit_text("✅ Образование сохранено!")
        await asyncio.sleep(1)
        
        step_num = 3
        total_steps = context.user_data['profile']['total_steps']
        await query.message.edit_text(
            f"❤️ Шаг {step_num}/{total_steps}: Интересы\n\n"
            "Напиши свои интересы через запятую (например: программирование, дизайн, музыка, спорт):",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💾 Сохранить", callback_data="save_interests")],
                [InlineKeyboardButton("❌ Пропустить", callback_data="skip_interests")]
            ])
        )
        
        context.user_data['waiting_for_interests'] = True
    else:
        profile = get_user_profile(user.id)
        if profile:
            profile['education'] = edu_mapping[data]
            save_user_profile(user.id, user.first_name, user.username, profile)
            await query.message.edit_text("✅ Образование обновлено!")
            await asyncio.sleep(1)
            await query.message.edit_text(
                "✏️ Профиль обновлен!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✏️ Редактировать еще", callback_data="edit_profile"),
                    InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
                ]])
            )

async def handle_skip_education(query, context: ContextTypes.DEFAULT_TYPE):
    """Пропуск образования"""
    await handle_education_selection(query, context, "edu_courses")

async def handle_save_interests(query, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение интересов"""
    if 'interests' not in context.user_data['profile']:
        context.user_data['profile']['interests'] = "программирование, дизайн, творчество"
    
    await query.message.edit_text("✅ Интересы сохранены!")
    await asyncio.sleep(1)

    await query.message.edit_text(
        "🛠️ Шаг 4/6: Навыки\n\n"
        "Напиши свои навыки через запятую (например: Python, PhotoShop, C++, C#):",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💾 Сохранить", callback_data="save_skills")],
            [InlineKeyboardButton("❌ Пропустить", callback_data="skip_skills")]
        ])
    )
    
    context.user_data['waiting_for_skills'] = True

async def handle_skip_interests(query, context: ContextTypes.DEFAULT_TYPE):
    """Пропуск интересов"""
    context.user_data['profile']['interests'] = "общие интересы"
    await handle_save_interests(query, context)

async def handle_save_skills(query, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение навыков"""
    if 'skills' not in context.user_data['profile']:
        context.user_data['profile']['skills'] = "коммуникации, работа в команде"
    
    await query.message.edit_text("✅ Навыки сохранены!")
    await asyncio.sleep(1)

    age_group = context.user_data['profile'].get('age_group', '')
    is_under_18 = age_group == "13-17 лет"
    
    if is_under_18:
        step_num = 4
        total_steps = context.user_data['profile']['total_steps']
        await query.message.edit_text(
            f"💼 Шаг {step_num}/{total_steps}: Подработка\n\n"
            "Есть ли у тебя опыт подработки? Напиши что-то вроде 'репетиторство', 'помощь в магазине' или 'нет опыта':",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💾 Сохранить", callback_data="save_current_job")],
                [InlineKeyboardButton("❌ Пропустить", callback_data="skip_current_job")]
            ])
        )
    else:
        step_num = 5
        total_steps = context.user_data['profile']['total_steps']
        await query.message.edit_text(
            f"💼 Шаг {step_num}/{total_steps}: Текущая работа\n\n"
            "Напиши свою текущую профессию или 'Безработный' если не работаешь:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💾 Сохранить", callback_data="save_current_job")],
                [InlineKeyboardButton("❌ Пропустить", callback_data="skip_current_job")]
            ])
        )
    
    context.user_data['waiting_for_current_job'] = True

async def handle_skip_skills(query, context: ContextTypes.DEFAULT_TYPE):
    """Пропуск навыков"""
    context.user_data['profile']['skills'] = "базовые навыки"
    await handle_save_skills(query, context)

async def handle_save_current_job(query, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение текущей работы"""
    if 'current_job' not in context.user_data['profile']:
        context.user_data['profile']['current_job'] = "Безработный"
    
    await query.message.edit_text("✅ Текущая работа сохранена!")
    await asyncio.sleep(1)
    
    age_group = context.user_data['profile'].get('age_group', '')
    is_under_18 = age_group == "13-17 лет"
    
    step_num = 5 if is_under_18 else 6
    total_steps = context.user_data['profile']['total_steps']
    
    if is_under_18:
        question_text = "Оцени свою удовлетворенность подработкой или учебой (1-5):"
    else:
        question_text = "Оцени свою удовлетворенность текущей работой (1-5):"
    
    await query.message.edit_text(
        f"😊 Шаг {step_num}/{total_steps}: Удовлетворенность\n\n"
        f"{question_text}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("😢 1", callback_data="satisfaction_1"),
             InlineKeyboardButton("😔 2", callback_data="satisfaction_2")],
            [InlineKeyboardButton("😐 3", callback_data="satisfaction_3"),
             InlineKeyboardButton("😊 4", callback_data="satisfaction_4")],
            [InlineKeyboardButton("😍 5", callback_data="satisfaction_5")],
            [InlineKeyboardButton("❌ Пропустить", callback_data="skip_satisfaction")]
        ])
    )

async def handle_skip_current_job(query, context: ContextTypes.DEFAULT_TYPE):
    """Пропуск текущей работы"""
    context.user_data['profile']['current_job'] = "Не указано"
    await handle_save_current_job(query, context)

async def handle_satisfaction_selection(query, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Обработка выбора удовлетворенности"""
    user = query.from_user
    record_interaction(user.id, "satisfaction_selection", data)
    
    satisfaction = int(data.split("_")[1])

    if 'profile' in context.user_data:
        context.user_data['profile']['satisfaction'] = satisfaction
        
        await query.message.edit_text("✅ Удовлетворенность сохранена!")
        await asyncio.sleep(1)
        
        await handle_complete_profile(query, context)

    else:
        profile = get_user_profile(user.id)
        if profile:
            profile['satisfaction'] = satisfaction
            save_user_profile(user.id, user.first_name, user.username, profile)
            await query.message.edit_text("✅ Удовлетворенность обновлена!")
            await asyncio.sleep(1)
            await query.message.edit_text(
                "✏️ Профиль обновлен!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✏️ Редактировать еще", callback_data="edit_profile"),
                    InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
                ]])
            )

async def handle_skip_satisfaction(query, context: ContextTypes.DEFAULT_TYPE):
    """Пропуск удовлетворенности"""
    context.user_data['profile']['satisfaction'] = 3
    await handle_satisfaction_selection(query, context, "satisfaction_3")

async def handle_complete_profile(query, context: ContextTypes.DEFAULT_TYPE):
    """Завершение создания профиля"""
    user = query.from_user
    profile = context.user_data['profile']
    
    save_user_profile(
        user.id, 
        user.first_name, 
        user.username, 
        profile
    )
    
    record_interaction(user.id, "profile_completed")

    await query.message.edit_text("🎉 Создаем твой профиль...")
    await asyncio.sleep(1)
    
    await query.message.edit_text("✨ Профиль успешно создан!")
    await asyncio.sleep(1)
    
    profile_text = "👤 Твой профиль создан!\n\n"
    profile_text += f"👶 Возрастная группа: {profile.get('age_group', 'Не указано')}\n"
    profile_text += f"🎓 Образование: {profile.get('education', 'Не указано')}\n"
    profile_text += f"❤️ Интересы: {profile.get('interests', 'Не указано')}\n"
    profile_text += f"🛠️ Навыки: {profile.get('skills', 'Не указано')}\n"
    profile_text += f"💼 Текущая работа: {profile.get('current_job', 'Не указано')}\n"
    profile_text += f"😊 Удовлетворенность: {profile.get('satisfaction', 'Не указано')}/5\n\n"
    profile_text += "🎯 Теперь ты можешь получать персональные рекомендации!"
    
    keyboard = [
        [InlineKeyboardButton("💡 Получить рекомендации", callback_data="recommendations")],
        [InlineKeyboardButton("🧠 Пройти тест", callback_data="test")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    
    await query.message.edit_text(
        profile_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    context.user_data.pop('profile', None)
    context.user_data.pop('waiting_for_interests', None)
    context.user_data.pop('waiting_for_skills', None)
    context.user_data.pop('waiting_for_current_job', None)

async def start_career_test(query, context: ContextTypes.DEFAULT_TYPE):
    """Начать карьерный тест"""
    user = query.from_user
    record_interaction(user.id, "start_career_test")
    
    questions = get_test_questions()
    context.user_data['test'] = {
        'questions': questions,
        'current_question': 0,
        'answers': {},
        'scores': {category: 0 for category in CAREER_CATEGORIES.keys()}
    }
    
    loading_msg = await query.message.reply_text("🔄 Подготавливаем тест...")
    await asyncio.sleep(1)
    
    await loading_msg.edit_text("🧠 Пишем вопросы...")
    await asyncio.sleep(1)
    
    await loading_msg.edit_text("✨ Тест готов! Начинаем...")
    await asyncio.sleep(1)
    
    await show_test_question(query, context)

async def show_test_question(query, context: ContextTypes.DEFAULT_TYPE):
    """Показать текущий вопрос теста"""
    test_data = context.user_data['test']
    current_q = test_data['current_question']
    questions = test_data['questions']
    
    if current_q >= len(questions):
        await finish_test(query, context)
        return
    
    question = questions[current_q]
    progress = f"Вопрос {current_q + 1}/{len(questions)}"
    
    buttons = []
    for i, option in enumerate(question['options']):
        buttons.append([InlineKeyboardButton(
            f"{i + 1}. {option}", 
            callback_data=f"test_answer_{i}"
        )])
    
    buttons.append([InlineKeyboardButton("🏁 Завершить тест", callback_data="finish_test")])
    
    text = f"🧠 {progress}\n\n"
    text += f"{question['question_text']}\n\n"
    text += "Выбери наиболее подходящий ответ:"
    
    await query.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def handle_test_answer(query, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Обработка ответа на вопрос теста"""
    user = query.from_user
    answer_index = int(data.split("_")[2])
    
    test_data = context.user_data['test']
    current_q = test_data['current_question']
    question = test_data['questions'][current_q]

    test_data['answers'][current_q] = answer_index

    weights_str = question['weights']
    for weight_pair in weights_str.split(','):
        if ':' in weight_pair:
            category, weight = weight_pair.split(':')
            test_data['scores'][category] += int(weight)
    
    record_interaction(user.id, "test_answer", f"q{current_q}_a{answer_index}")
    
    selected_option = question['options'][answer_index]
    await query.message.edit_text(f"✅ Выбрано: {selected_option}")
    await asyncio.sleep(1)
    
    test_data['current_question'] += 1
    
    if test_data['current_question'] < len(test_data['questions']):

        progress_text = f"📊 Прогресс: {test_data['current_question']}/{len(test_data['questions'])}"
        await query.message.edit_text(progress_text)
        await asyncio.sleep(1)
        await show_test_question(query, context)
    else:
        await finish_test(query, context)

async def handle_finish_test(query, context: ContextTypes.DEFAULT_TYPE):
    """Завершение теста"""
    await finish_test(query, context)

async def finish_test(query, context: ContextTypes.DEFAULT_TYPE):
    """Завершение и анализ результатов теста"""
    user = query.from_user
    test_data = context.user_data['test']
    
    await query.message.edit_text("🔄 Анализируем твои ответы...")
    await asyncio.sleep(2)
    
    await query.message.edit_text("🧠 Подсчитываем баллы...")
    await asyncio.sleep(2)
    
    await query.message.edit_text("📊 Определяем твои склонности...")
    await asyncio.sleep(2)
    
    save_test_results(user.id, test_data['scores'])
    
    sorted_scores = sorted(test_data['scores'].items(), key=lambda x: x[1], reverse=True)
    top_categories = sorted_scores[:3]
    
    result_text = "🎉 Результаты карьерного теста\n\n"
    result_text += "📊 Твои склонности:\n\n"
    
    for i, (category, score) in enumerate(top_categories, 1):
        category_name = CAREER_CATEGORIES.get(category, category)
        percentage = (score / sum(test_data['scores'].values())) * 100 if sum(test_data['scores'].values()) > 0 else 0

        emoji_map = {
            "IT": "💻",
            "CREATIVE": "🎨", 
            "BUSINESS": "💼",
            "SCIENCE": "🔬",
            "MEDICAL": "🏥",
            "TECHNICAL": "🔧",
            "SERVICE": "🤝"
        }
        
        emoji = emoji_map.get(category, "📈")
        result_text += f"{emoji} {i}. {category_name} - {percentage:.1f}%\n"
    
    result_text += f"\n✅ Тест завершен! Ответов: {len(test_data['answers'])}/{len(test_data['questions'])}\n\n"
    result_text += "💡 Теперь ты можешь получить персональные рекомендации на основе результатов теста!"
    
    keyboard = [
        [InlineKeyboardButton("💡 Получить рекомендации", callback_data="recommendations")],
        [InlineKeyboardButton("🔍 Поиск профессий", callback_data="search")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    
    await query.message.edit_text(
        result_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    record_interaction(user.id, "test_completed", f"scores_{test_data['scores']}")
    context.user_data.pop('test', None)

async def handle_edit_age(query, context: ContextTypes.DEFAULT_TYPE):
    """Редактирование возрастной группы"""
    user = query.from_user
    record_interaction(user.id, "edit_age")
    
    await query.message.edit_text(
        "👶 Редактирование возрастной группы\n\n"
        "Выбери новую возрастную группу:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("13-17 лет", callback_data="age_13_17")],
            [InlineKeyboardButton("18-24 года", callback_data="age_18_24")],
            [InlineKeyboardButton("25-35 лет", callback_data="age_25_35")],
            [InlineKeyboardButton("36+ лет", callback_data="age_36_plus")],
            [InlineKeyboardButton("🔙 Назад", callback_data="edit_profile")]
        ])
    )

async def handle_edit_education(query, context: ContextTypes.DEFAULT_TYPE):
    """Редактирование образования"""
    user = query.from_user
    record_interaction(user.id, "edit_education")
    
    await query.message.edit_text(
        "🎓 Редактирование образования\n\n"
        "Выбери новый уровень образования:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏫 Школа", callback_data="edu_school")],
            [InlineKeyboardButton("🎓 ВУЗ", callback_data="edu_university")],
            [InlineKeyboardButton("📚 Курсы", callback_data="edu_courses")],
            [InlineKeyboardButton("💼 Опыт работы", callback_data="edu_experience")],
            [InlineKeyboardButton("🔙 Назад", callback_data="edit_profile")]
        ])
    )

async def handle_edit_interests(query, context: ContextTypes.DEFAULT_TYPE):
    """Редактирование интересов"""
    user = query.from_user
    record_interaction(user.id, "edit_interests")
    
    await query.message.edit_text(
        "❤️ Редактирование интересов\n\n"
        "Напиши новые интересы через запятую:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Назад", callback_data="edit_profile")]
        ])
    )
    
    context.user_data['editing_interests'] = True

async def handle_edit_skills(query, context: ContextTypes.DEFAULT_TYPE):
    """Редактирование навыков"""
    user = query.from_user
    record_interaction(user.id, "edit_skills")
    
    await query.message.edit_text(
        "🛠️ Редактирование навыков\n\n"
        "Напиши новые навыки через запятую:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Назад", callback_data="edit_profile")]
        ])
    )
    
    context.user_data['editing_skills'] = True

async def handle_edit_current_job(query, context: ContextTypes.DEFAULT_TYPE):
    """Редактирование текущей работы"""
    user = query.from_user
    record_interaction(user.id, "edit_current_job")
    
    await query.message.edit_text(
        "💼 Редактирование текущей работы\n\n"
        "Напиши новую профессию или 'Безработный':",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Назад", callback_data="edit_profile")]
        ])
    )
    
    context.user_data['editing_current_job'] = True

async def handle_edit_satisfaction(query, context: ContextTypes.DEFAULT_TYPE):
    """Редактирование удовлетворенности"""
    user = query.from_user
    record_interaction(user.id, "edit_satisfaction")
    
    await query.message.edit_text(
        "😊 Редактирование удовлетворенности\n\n"
        "Оцени свою удовлетворенность работой (1-5):",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("😢 1", callback_data="satisfaction_1"),
             InlineKeyboardButton("😔 2", callback_data="satisfaction_2")],
            [InlineKeyboardButton("😐 3", callback_data="satisfaction_3"),
             InlineKeyboardButton("😊 4", callback_data="satisfaction_4")],
            [InlineKeyboardButton("😍 5", callback_data="satisfaction_5")],
            [InlineKeyboardButton("🔙 Назад", callback_data="edit_profile")]
        ])
    )

async def handle_delete_profile(query, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение удаления профиля"""
    user = query.from_user
    record_interaction(user.id, "delete_profile_request")
    
    await query.message.edit_text(
        "⚠️ Удаление профиля\n\n"
        "Ты уверен, что хочешь удалить свой профиль?\n"
        "Это действие нельзя отменить!\n\n"
        "Все твои данные будут удалены: профиль, результаты тестов, история взаимодействий.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ Да, удалить", callback_data="confirm_delete")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel_delete")]
        ])
    )

async def handle_confirm_delete(query, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение удаления профиля"""
    user = query.from_user
    record_interaction(user.id, "profile_deleted")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("DELETE FROM users WHERE user_id = ?", (user.id,))
    c.execute("DELETE FROM user_test_results WHERE user_id = ?", (user.id,))
    c.execute("DELETE FROM interactions WHERE user_id = ?", (user.id,))
    
    conn.commit()
    conn.close()
    
    await query.message.edit_text("🗑️ Удаляем профиль...")
    await asyncio.sleep(1)
    
    await query.message.edit_text("✅ Профиль успешно удален!")
    await asyncio.sleep(1)
    
    await query.message.edit_text(
        "👋 Твой профиль удален.\n\n"
        "Если захочешь создать новый профиль, используй команду /start",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ]])
    )

async def handle_cancel_delete(query, context: ContextTypes.DEFAULT_TYPE):
    """Отмена удаления профиля"""
    user = query.from_user
    record_interaction(user.id, "delete_cancelled")
    
    await query.message.edit_text(
        "✅ Удаление отменено!\n\n"
        "Твой профиль сохранен.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✏️ Редактировать профиль", callback_data="edit_profile"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ]])
    )

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений для поиска и создания профиля"""
    user = update.effective_user
    text = update.message.text

    if context.user_data.get('waiting_for_search'):
        context.user_data['waiting_for_search'] = False
        await handle_search_query(update, context)
    elif context.user_data.get('waiting_for_vacancy_search'):
        context.user_data['waiting_for_vacancy_search'] = False
        await handle_vacancy_search(update, context)
    elif context.user_data.get('waiting_for_interests'):
        context.user_data['profile']['interests'] = text
        context.user_data['waiting_for_interests'] = False
        await update.message.reply_text("✅ Интересы сохранены! Переходим к навыкам...")
        await asyncio.sleep(1)
        await update.message.reply_text(
            "🛠️ Шаг 4/6: Навыки\n\n"
            "Напиши свои навыки через запятую (например: Python, Photoshop, английский язык):",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💾 Сохранить", callback_data="save_skills")],
                [InlineKeyboardButton("❌ Пропустить", callback_data="skip_skills")]
            ])
        )
        context.user_data['waiting_for_skills'] = True
    elif context.user_data.get('waiting_for_skills'):
        context.user_data['profile']['skills'] = text
        context.user_data['waiting_for_skills'] = False
        await update.message.reply_text("✅ Навыки сохранены! Переходим к последнему шагу...")
        await asyncio.sleep(1)
        await update.message.reply_text(
            "💼 Шаг 5/6: Текущая работа\n\n"
            "Напиши свою текущую профессию или 'Безработный' если не работаешь:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💾 Сохранить", callback_data="save_current_job")],
                [InlineKeyboardButton("❌ Пропустить", callback_data="skip_current_job")]
            ])
        )
        context.user_data['waiting_for_current_job'] = True
    elif context.user_data.get('waiting_for_current_job'):
        context.user_data['profile']['current_job'] = text
        context.user_data['waiting_for_current_job'] = False
        await update.message.reply_text("✅ Текущая работа сохранена! Переходим к последнему шагу...")
        await asyncio.sleep(1)
        await update.message.reply_text(
            "😊 Шаг 6/6: Удовлетворенность работой\n\n"
            "Оцени свою удовлетворенность текущей работой (1-5):",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("😢 1", callback_data="satisfaction_1"),
                 InlineKeyboardButton("😔 2", callback_data="satisfaction_2")],
                [InlineKeyboardButton("😐 3", callback_data="satisfaction_3"),
                 InlineKeyboardButton("😊 4", callback_data="satisfaction_4")],
                [InlineKeyboardButton("😍 5", callback_data="satisfaction_5")],
                [InlineKeyboardButton("❌ Пропустить", callback_data="skip_satisfaction")]
            ])
        )
    elif context.user_data.get('editing_interests'):
        profile = get_user_profile(user.id)
        if profile:
            profile['interests'] = text
            save_user_profile(user.id, user.first_name, user.username, profile)
            await update.message.reply_text("✅ Интересы обновлены!")
            await asyncio.sleep(1)
            await update.message.reply_text(
                "✏️ Профиль обновлен!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✏️ Редактировать еще", callback_data="edit_profile"),
                    InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
                ]])
            )
        context.user_data['editing_interests'] = False
    elif context.user_data.get('editing_skills'):
        profile = get_user_profile(user.id)
        if profile:
            profile['skills'] = text
            save_user_profile(user.id, user.first_name, user.username, profile)
            await update.message.reply_text("✅ Навыки обновлены!")
            await asyncio.sleep(1)
            await update.message.reply_text(
                "✏️ Профиль обновлен!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✏️ Редактировать еще", callback_data="edit_profile"),
                    InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
                ]])
            )
        context.user_data['editing_skills'] = False
    elif context.user_data.get('editing_current_job'):
        profile = get_user_profile(user.id)
        if profile:
            profile['current_job'] = text
            save_user_profile(user.id, user.first_name, user.username, profile)
            await update.message.reply_text("✅ Текущая работа обновлена!")
            await asyncio.sleep(1)
            await update.message.reply_text(
                "✏️ Профиль обновлен!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✏️ Редактировать еще", callback_data="edit_profile"),
                    InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
                ]])
            )
        context.user_data['editing_current_job'] = False
    else:
        await start_command(update, context)

def get_test_questions() -> List[Dict]:
    """Получить все тестовые вопросы"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    SELECT id, question_text, options, weights, category, order_num
    FROM test_questions ORDER BY order_num
    """)
    
    rows = c.fetchall()
    conn.close()
    
    questions = []
    for row in rows:
        questions.append({
            "id": row[0],
            "question_text": row[1],
            "options": row[2].split(","),
            "weights": row[3],
            "category": row[4],
            "order_num": row[5]
        })
    return questions

def save_test_results(user_id: int, results: Dict[str, int]):
    """Сохранить результаты теста"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("DELETE FROM user_test_results WHERE user_id = ?", (user_id,))
    
    now = datetime.utcnow().isoformat()
    for category, score in results.items():
        c.execute("""
        INSERT INTO user_test_results(user_id, category, score, test_date)
        VALUES(?,?,?,?)
        """, (user_id, category, score, now))
    
    conn.commit()
    conn.close()

def get_user_test_results(user_id: int) -> Optional[Dict[str, int]]:
    """Получить результаты теста пользователя"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    SELECT category, score FROM user_test_results WHERE user_id = ?
    """, (user_id,))
    
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        return None
    
    return {row[0]: row[1] for row in rows}

def get_careers_by_category(category: str = None) -> List[Dict]:
    """Получить профессии по категории"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if category:
        c.execute("""
        SELECT id, name, category, description, skills_required, education_level, 
               salary_range, tags, learning_resources
        FROM careers WHERE category = ?
        """, (category,))
    else:
        c.execute("""
        SELECT id, name, category, description, skills_required, education_level, 
               salary_range, tags, learning_resources
        FROM careers
        """)
    
    rows = c.fetchall()
    conn.close()
    
    careers = []
    for row in rows:
        careers.append({
            "id": row[0],
            "name": row[1],
            "category": row[2],
            "description": row[3],
            "skills_required": row[4].split(",") if row[4] else [],
            "education_level": row[5],
            "salary_range": row[6],
            "tags": row[7].split(",") if row[7] else [],
            "learning_resources": row[8].split(",") if row[8] else []
        })
    return careers

def search_careers(query: str) -> List[Dict]:
    """Поиск профессий по запросу"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    search_term = f"%{query.lower()}%"
    c.execute("""
    SELECT id, name, category, description, skills_required, education_level, 
           salary_range, tags, learning_resources
    FROM careers 
    WHERE LOWER(name) LIKE ? OR LOWER(description) LIKE ? OR LOWER(tags) LIKE ? OR LOWER(skills_required) LIKE ?
    """, (search_term, search_term, search_term, search_term))
    
    rows = c.fetchall()
    conn.close()
    
    careers = []
    for row in rows:
        careers.append({
            "id": row[0],
            "name": row[1],
            "category": row[2],
            "description": row[3],
            "skills_required": row[4].split(",") if row[4] else [],
            "education_level": row[5],
            "salary_range": row[6],
            "tags": row[7].split(",") if row[7] else [],
            "learning_resources": row[8].split(",") if row[8] else []
        })
    return careers

def main():
    """Запуск бота"""
    print("Starting Career Advisor Bot...")
    
    init_database()
    print("Database initialized")
    
    seed_careers()
    seed_test_questions()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler("test", test_command))
    application.add_handler(CommandHandler("recommendations", recommendations_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("vacancies", vacancies_command))
    
    application.add_handler(CallbackQueryHandler(button_callback))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    search_conversation = ConversationHandler(
        entry_points=[CommandHandler("search", search_command)],
        states={
            SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search_query)]
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)]
    )
    application.add_handler(search_conversation)
    
    vacancy_conversation = ConversationHandler(
        entry_points=[CommandHandler("vacancies", vacancies_command)],
        states={
            SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_vacancy_search)]
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)]
    )
    application.add_handler(vacancy_conversation)
    
    print("Bot started and ready to work!")
    application.run_polling()

async def handle_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка поискового запроса"""
    query = update.message.text
    user_id = update.effective_user.id
    
    record_interaction(user_id, "search_query", query)

    loading_msg = await update.message.reply_text(f"🔍 Ищу профессии по запросу '{query}'...")
    await asyncio.sleep(1)
    
    await loading_msg.edit_text("📚 Просматриваю базу профессий...")
    await asyncio.sleep(1)
    
    await loading_msg.edit_text("🔍 Анализирую совпадения...")
    await asyncio.sleep(1)

    careers = search_careers(query)
    
    if not careers:
        await loading_msg.edit_text(
            f"😔 По запросу '{query}' ничего не найдено! \n\n"
            "Попробуй другие ключевые слова:\n"
            "• 'программист', 'разработчик'\n"
            "• 'дизайн', 'творчество'\n"
            "• 'медицина', 'врач'\n"
            "• 'бизнес', 'менеджер'",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔍 Новый поиск", callback_data="search"),
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]])
        )
        return

    await loading_msg.edit_text("✨ Профессии найдены!")
    await asyncio.sleep(1)

    text = f"🎯 Результаты поиска по запросу '{query}':\n\n"
    
    for i, career in enumerate(careers[:5], 1):
        category_emoji = {
            "IT и технологии": "💻",
            "Творчество и дизайн": "🎨",
            "Бизнес и управление": "💼",
            "Наука и образование": "🔬",
            "Медицина и здоровье": "🏥",
            "Рабочие специальности": "🔧",
            "Сфера услуг": "🤝"
        }
        
        emoji = category_emoji.get(career['category'], "📈")
        
        text += f"{emoji} {i}. {career['name']}\n"
        text += f"📂 {career['category']}\n"
        text += f"💰 {career['salary_range']} руб/мес\n"
        text += f"📝 {career['description'][:80]}...\n"
        
        if career['skills_required']:
            skills_text = ", ".join(career['skills_required'][:3])
            text += f"🛠️ {skills_text}\n"
        
        text += f"🎓 {career['education_level']}\n\n"
    
    if len(careers) > 5:
        text += f"... и еще {len(careers) - 5} профессий\n\n"
    
    text += "💡 Хочешь узнать больше? Используй поиск с более конкретным запросом"
    
    keyboard = [
        [InlineKeyboardButton("🔍 Новый поиск", callback_data="search")],
        [InlineKeyboardButton("💡 Рекомендации", callback_data="recommendations")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    
    await loading_msg.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return ConversationHandler.END

def search_hh_vacancies(query: str, limit: int = 5) -> List[Dict]:
    """Поиск вакансий на HH.ru"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
        SELECT vacancy_data FROM parsed_vacancies 
        WHERE query = ? AND expires_at > ?
        """, (query, datetime.utcnow().isoformat()))
        
        cached_result = c.fetchone()
        if cached_result:
            conn.close()
            return json.loads(cached_result[0])

        params = {
            'text': query,
            'area': 1,
            'per_page': limit,
            'only_with_salary': True
        }
        
        response = requests.get(HH_API_URL, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        vacancies = []
        
        for item in data.get('items', []):
            salary = item.get('salary', {})
            salary_text = "Не указана"
            
            if salary:
                from_salary = salary.get('from')
                to_salary = salary.get('to')
                currency = salary.get('currency', 'RUR')
                
                if from_salary and to_salary:
                    salary_text = f"{from_salary:,} - {to_salary:,} {currency}"
                elif from_salary:
                    salary_text = f"от {from_salary:,} {currency}"
                elif to_salary:
                    salary_text = f"до {to_salary:,} {currency}"
            
            vacancy = {
                'name': item.get('name', 'Без названия'),
                'company': item.get('employer', {}).get('name', 'Не указана'),
                'salary': salary_text,
                'url': item.get('alternate_url', ''),
                'description': item.get('snippet', {}).get('requirement', '')[:100] + '...'
            }
            vacancies.append(vacancy)

        expires_at = (datetime.utcnow() + timedelta(hours=24)).isoformat()
        c.execute("""
        INSERT INTO parsed_vacancies(query, vacancy_data, created_at, expires_at)
        VALUES(?,?,?,?)
        """, (query, json.dumps(vacancies), datetime.utcnow().isoformat(), expires_at))
        
        conn.commit()
        conn.close()
        
        return vacancies
        
    except Exception as e:
        print(f"Ошибка поиска вакансий: {e}")
        return []


async def handle_vacancy_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка поиска вакансий"""
    query = update.message.text
    user_id = update.effective_user.id
    
    record_interaction(user_id, "vacancy_search", query)

    loading_msg = await update.message.reply_text(f"🔍 Ищу вакансии по запросу '{query}'...")
    await asyncio.sleep(1)
    
    await loading_msg.edit_text("🌐 Подключаемся к HH.ru...")
    await asyncio.sleep(1)
    
    vacancies = search_hh_vacancies(query, limit=5)
    
    await loading_msg.edit_text("📊 Анализируем вакансии...")
    await asyncio.sleep(1)
    
    await loading_msg.edit_text("💼 Обрабатываем результаты...")
    await asyncio.sleep(1)
    
    if not vacancies:
        await loading_msg.edit_text(
            f"😔 По запросу '{query}' вакансии не найдены на HH.ru!\n\n"
            "Попробуй:\n"
            "• Более общие запросы: 'программист', 'менеджер', 'сварщик', 'строитель', 'механик', 'электрик', 'инженер'\n"
            "• Конкретные технологии: 'Python', 'JavaScript', 'C#', 'C++', 'SQL', 'HTML', 'CSS', 'React'\n"
            "• Сферы: 'маркетинг', 'дизайн', 'бизнес', 'наука', 'образование', 'медицина'",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔍 Новый поиск", callback_data="vacancies"),
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]])
        )
        return

    await loading_msg.edit_text("✨ Вакансии найдены!")
    await asyncio.sleep(1)

    text = f"💼 Актуальные вакансии по запросу '{query}' (HH.ru):\n\n"
    
    for i, vacancy in enumerate(vacancies, 1):
        text += f"{i}. {vacancy['name']}\n"
        text += f"🏢 {vacancy['company']}\n"
        text += f"💰 {vacancy['salary']}\n"
        text += f"📝 {vacancy['description']}\n"
        text += f"🔗 [Подробнее]({vacancy['url']})\n\n"
    
    text += "💡 Данные HH.ru обновляются каждые 24 часа"
    
    keyboard = [
        [InlineKeyboardButton("🔍 Новый поиск", callback_data="vacancies")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    
    await loading_msg.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    context.user_data.pop('search_platform', None)
    
    return ConversationHandler.END

if __name__ == "__main__":
    main()