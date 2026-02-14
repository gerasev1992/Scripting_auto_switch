import requests
from bs4 import BeautifulSoup
import re
import sys
import datetime
import pickle

class CRMAuthenticator:
    def __init__(self, base_url="https://xxx.yyy/"):#Ваш URL
        self.base_url = base_url
        self.session = requests.Session()
        self.logged_in = False
    
    def login(self, username, password):
        try:
            #Получаем страницу входа
            response = self.session.get(self.base_url)
            if response.status_code != 200:
                print(f"Ошибка: Не удалось получить страницу входа ({response.status_code})")
                return False
            soup = BeautifulSoup(response.text, 'html.parser')
            #Ищем форму входа
            login_form = self._find_login_form(soup)
            if not login_form:
                print("Форма входа не найдена. Пробуем стандартный подход...")
                # Пробуем прямую отправку данных
                return self._try_direct_login(username, password)
            #Подготавливаем данные формы
            form_data = self._prepare_form_data(login_form, username, password)
            #Определяем URL для отправки
            submit_url = self._get_submit_url(login_form)
            #Отправляем форму
            headers = {
                'Referer': self.base_url
            }
            response = self.session.post(submit_url, data=form_data, headers=headers)
            #Проверяем результат
            if response.status_code == 200:
                self.logged_in = self._check_login_success(response.text)
                if self.logged_in:
                    print("Вход выполнен успешно!")
                    return True
                else:
                    return False
            else:
                print(f"\nОшибка при входе: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"\nОшибка сети: {e}")
            return False
        except Exception as e:
            print(f"\n Неожиданная ошибка: {e}")
            return False
    
    def _find_login_form(self, soup):
        # Ищем по разным признакам
        forms = soup.find_all('form')
        for form in forms:
            # Проверяем наличие полей пароля
            if form.find('input', {'type': 'password'}):
                return form
            # Или по имени поля
            if form.find('input', {'name': lambda x: x and 'pass' in x.lower()}):
                return form
        # Поиск по ID или классу
        login_form = soup.find('form', {'id': ['login-form', 'auth-form']})
        if login_form:
            return login_form
        login_form = soup.find('form', {'class': lambda x: x and any(cls in x.lower() for cls in ['login', 'auth'])})
        return login_form
    
    def _prepare_form_data(self, form, username, password):
        form_data = {}
        # Собираем все поля формы
        for input_tag in form.find_all('input'):
            name = input_tag.get('name')
            if not name:
                continue  
            input_type = input_tag.get('type', '').lower()
            value = input_tag.get('value', '')
            # Заполняем логин
            if input_type == 'text':
                if any(keyword in name.lower() for keyword in ['user', 'login', 'name']):
                    form_data[name] = username
                else:
                    form_data[name] = value
            # Заполняем пароль
            elif input_type == 'password':
                form_data[name] = password
            # Сохраняем скрытые поля
            elif input_type == 'hidden':
                form_data[name] = value
            # Кнопки отправки
            elif input_type in ['submit', 'button']:
                if not any(key in form_data for key in ['submit', 'login', 'enter']):
                    form_data[name] = value
        return form_data
    
    def _get_submit_url(self, form):
        action = form.get('action')
        if not action:
            return self.base_url
        if action.startswith('https'):
            return action
        elif action.startswith('/'):
            return self.base_url.rstrip('/') + action
        else:
            return self.base_url.rstrip('/') + '/' + action.lstrip('/')
    
    def _check_login_success(self, page_content):
        soup = BeautifulSoup(page_content, 'html.parser')
        # Проверяем наличие индикаторов успешного входа
        success_indicators = [
            'выход', 'logout', 'выйти', 'профиль', 'profile',
            'личный кабинет', 'кабинет', 'dashboard'
        ]
        # Ищем текст, указывающий на успешный вход
        page_text = soup.get_text().lower()
        for indicator in success_indicators:
            if indicator in page_text:
                return True
        # Ищем кнопку выхода
        logout_elements = soup.find_all(['a', 'button'], text=lambda x: x and any(word in x.lower() for word in ['выход', 'logout', 'выйти']))
        if logout_elements:
            return True
        return False
    
    def navigate_to_project(self, project_id):"):
        if not self.logged_in:
            print("Сначала необходимо выполнить вход!")
            return False, None, None
        # Формируем URL страницы проекта
        project_url = f"https://xxx/yyy.{project_id}"
        print(f"{'='*60}")
        print(f"ID проекта: {project_id}")
        print(f"URL: {project_url}")
        print(f"{'='*60}")
        try:
            # Переходим на страницу проекта
            headers = {
                'Referer': self.base_url
            }
            response = self.session.get(project_url, headers=headers)
            if response.status_code != 200:
                print(f"Ошибка загрузки страницы: {response.status_code}")
                return False, None, None
            unit_port_data = self._find_unit_port_values(response.text)
            data_data = self._find_data_numbers(response.text)
            found = True
            if found:
                return True, [], unit_port_data, data_data            
            else:
                return False, [], unit_port_data, data_data                         
        except Exception as e:
            return False, [], unit_port_data, data_data
    
    def _search_text_on_page(self, page_content, search_text):
        soup = BeautifulSoup(page_content, 'html.parser')
        found_matches = []
        #Поиск точного текста (регистронезависимый)
        exact_matches = soup.find_all(text=re.compile(re.escape(search_text), re.IGNORECASE))
        if exact_matches:
            for match in exact_matches:
                text = match.strip()
                if text:
                    found_matches.append(text)
            return True, found_matches
        return False, found_matches
    
    def _find_unit_port_values(self, page_content):
        soup = BeautifulSoup(page_content, 'html.parser')
        all_text = soup.get_text()
        # РАСШИРЕННЫЙ паттерн для поиска значений с разными вариантами написания
        patterns = [
            # Стандартный формат: Unit/Порт U83.119-eth-5
            r'Unit/Порт\s+((?:[Gg][Ee]|U|MTT)[\d\.]+-\w+(?:-\w+)?)',
            # Формат с пробелами: U21.111 - eth - 15
            r'(?:Unit/Порт\s+)?((?:[Gg][Ee]|U|MTT)[\d\.]+\s*-\s*\w+\s*-\s*\w+)',
            # Формат без "Unit/Порт": U21.111-eth-15
            r'\b((?:[Gg][Ee]|U|MTT)[\d\.]+[-\s]\w+[-\s]\w+)\b',
            # Формат с разными интерфейсами
            r'(?:Unit/Порт\s+)?((?:[Gg][Ee]|U|MTT)[\d\.]+[-\s]\w+[-\s]?\w*)'
        ]
        all_matches = []
        for pattern in patterns:
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            for match in matches:
                # Проверяем, не добавляли ли уже это значение
                if match not in all_matches:
                    all_matches.append(match)
        if not all_matches:
            # Попробуем более широкий поиск
            print("Не найдено по основным паттернам, пробуем расширенный поиск...")
            # Альтернативный паттерн
            alt_pattern = r'Unit[-\s/]*Порт[:\s]+([Gg][Ee][UMTT\d\.\-\s]+)'
            alt_matches = re.findall(alt_pattern, all_text, re.IGNORECASE)
            for match in alt_matches:
                if match not in all_matches:
                    all_matches.append(match)
            if not all_matches:
                print("Значения Unit/Порт не найдены")
                return []
        processed_values = []
        for i, match in enumerate(all_matches, 1):
            # Убираем лишние пробелы
            clean_match = re.sub(r'\s+', ' ', match.strip())           
            # Извлекаем значение до первого дефиса (учитываем пробелы вокруг дефиса)
            parts = re.split(r'\s*-\s*', clean_match)
            value_before_dash = parts[0] if parts else clean_match           
            # Ищем номер порта с разными вариантами написания
            port_number = self._extract_port_number_improved(clean_match)    
            # Определяем тип значения (U или MTT)
            if value_before_dash.startswith('U'):
                prefix = 'U'
                # Извлекаем ВСЕ после 'U' до первого дефиса (включая точку)
                number_part = value_before_dash[1:]  # Убираем 'U'
                ip_base = "10.0"
                print(f"Тип: U-оборудование")
            elif value_before_dash.startswith('MTT'):
                prefix = 'MTT'
                # Извлекаем ВСЕ после 'MTT' до первого дефиса (включая точку)
                number_part = value_before_dash[3:]  # Убираем 'MTT'
                ip_base = "10.90"
                print(f"Тип: MTT-оборудование")
            elif value_before_dash.startswith('GE'):
                prefix = 'GE'
                # Извлекаем ВСЕ после 'GE' до первого дефиса (включая точку)
                number_part = value_before_dash[2:]  # Убираем 'GE'
                ip_base = "10.0"
                print(f"Тип: GE-оборудование")                
            else:
                print(f"Неизвестный тип значения: {value_before_dash}")
                continue
            # Формируем IP адрес по правилам
            if '.' in number_part:
                # Разделяем по точке и берем часть до точки
                first_part = number_part
                ip_address = f"{ip_base}.{first_part}"
                # Сохраняем переменные в файл
                with open("vars.pkl", "wb") as f:
                    pickle.dump({"ip_address" : ip_address, "port_number" : port_number}, f)
                (f"ip_address = {ip_address}")
                processed_values.append({
                    'original': match,
                    'clean_match': clean_match,
                    'value_before_dash': value_before_dash,
                    'prefix': prefix,
                    'number_part': number_part,  # Сохраняем с точкой
                    'ip_address': ip_address,
                    'port_number': port_number,  # Добавляем номер порта
                    'full_text': f"Unit/Порт {clean_match}" if "Unit/Порт" not in match else match,
                    'note': f"Взята часть до точки: {first_part}"
                })
            else:
                print(f"Первая часть '{first_part}' не является числом")
        else:
            # Если точки нет, используем все число
            if number_part.isdigit():
                ip_address = f"{ip_base}.{number_part}"
                print(f"Сформированный IP: {ip_address}")

                processed_values.append({
                    'original': match,
                    'clean_match': clean_match,
                    'value_before_dash': value_before_dash,
                    'prefix': prefix,
                    'number_part': number_part,
                    'ip_address': ip_address,
                    'port_number': port_number,  # Добавляем номер порта
                    'full_text': f"Unit/Порт {clean_match}" if "Unit/Порт" not in match else match,
                    'note': "Точки нет, использовано всё число"
                })
            else:
                print()
        return processed_values
    
    def _extract_port_number_improved(self, unit_port_value):
        # Убираем лишние пробелы
        clean_value = re.sub(r'\s+', ' ', unit_port_value.strip())
        # Паттерны для поиска порта с разными вариантами написания
        patterns = [
            # eth-5 или eth - 5
            r'eth[-\s]+(\d+)',
            # gi-3 или gi - 3
            r'gi[-\s]+(\d+)',
            # fa-1 или fa - 1
            r'fa[-\s]+(\d+)',
            # te-2 или te - 2
            r'te[-\s]+(\d+)',
            # ge-4 или ge - 4
            r'ge[-\s]+(\d+)',
            # Любой интерфейс с дефисом или пробелом
            r'[a-z]+[-\s]+(\d+)',
            # Цифры в конце строки после последнего дефиса/пробела
            r'[-\s]+(\d+)$',
            # Просто цифры в конце
            r'(\d+)$'
        ]
        for pattern in patterns:
            match = re.search(pattern, clean_value, re.IGNORECASE)
            if match:
                return match.group(1)
        return "не найден"
    
    def _find_data_numbers(self, page_content):     
        soup = BeautifulSoup(page_content, 'html.parser')
        all_text = soup.get_text()
        # Простой поиск "кв. число" или "пом. число"
        data_matches = []
        # Паттерн для поиска "кв. число" (квартира)
        kv_pattern = r'кв[a-zA-Zа-яА-Я]*\.\s*(\d+)'
        kv_matches = re.findall(kv_pattern, all_text, re.IGNORECASE)
        for match in kv_matches:
            data_matches.append({
                'type': 'квартира',
                'number': match,
                'full_text': f"кв. {match}",
                'note': 'Найдено по паттерну "кв. число"'
            })
            # Сохраняем переменные в файл
        with open("vars_kv.pkl", "wb") as f:
            pickle.dump({"kvartira" : match}, f)
        pom_pattern = r'ком[a-zA-Zа-яА-Я]+\.\s*(\d+)'
        pom_matches = re.findall(pom_pattern, all_text, re.IGNORECASE)
        for match in pom_matches:
            data_matches.append({
                'type': 'комната',
                'number': match,
                'full_text': f"ком. {match}",
                'note': 'Найдено по паттерну "ком. число"'
            })
        date_pattern = r'Дата выполнения\s*(\d+\.\d+\.\d+)'
        date_matches = re.findall(date_pattern, all_text, re.IGNORECASE)
        date_value = None
        if date_matches:
            for match in date_matches:
                data_matches.append({
                    'type': 'Дата выполнения',
                    'number': match,
                    'full_text': f"date. {match}",
                    'note': 'Найдено по паттерну "date"'
                })
            date_value = date_matches[0] if date_matches else None
        else:
            print(f"Паттерн 'Дата выполнения' {date_value} не найден")
            date_value = None
        with open("vars_date.pkl", "wb") as f:
            pickle.dump({"date" : date_value}, f)    
        down_pattern = r'\bОтключение\b'
        down_matches = re.findall(down_pattern, all_text, re.IGNORECASE)
        down_value = None
        if down_matches:
            for match in down_matches:
                data_matches.append({
                    'type': 'Отключение',
                    'number': match,
                    'full_text': f"down. {match}",
                    'note': 'Найдено по паттерну "down"'
                })
            down_value = down_matches[0] if down_matches else None
        else:
            print("Паттерн 'Отключение' не найден")
            down_value = None
        with open("vars_down.pkl", "wb") as f:
            pickle.dump({"down" : down_value}, f)        
        req_pattern = r'по\s*заявлению'
        req_matches = re.findall(req_pattern, all_text, re.IGNORECASE)
        # Инициализируем переменную для сохранения
        req_value = None
        if req_matches:
            for match in req_matches:
                data_matches.append({
                    'type': 'по заявлению',
                    'number': match,
                    'full_text': f"req. {match}",
                    'note': 'Найдено по паттерну "req"'
                })
            # Берем первое найденное значение (или можно выбрать нужную логику)
            req_value = req_matches[0] if req_matches else None
        else:
            print("Паттерн 'Причина' не найден")
            req_value = None
        with open("vars_req.pkl", "wb") as f:
            pickle.dump({"req": req_value}, f)
        # Удаляем дубликаты
        unique_matches = []
        seen = set()
        for match in data_matches:
            key = (match['type'], match['number'])
            if key not in seen:
                seen.add(key)
                unique_matches.append(match)
        return unique_matches
    
    def get_session_info(self):
        if not self.logged_in:
            return "Не авторизован"
        cookies = self.session.cookies.get_dict()
        return f"Авторизован. Cookies: {len(cookies)} шт."

def get_input_with_default(prompt, default_value=""):
    if default_value:
        user_input = input(f"{prompt} [{default_value}]: ").strip()
        return user_input if user_input else default_value
    else:
        return input(f"{prompt}: ").strip()

def display_unit_port_results(unit_port_data):
    if not unit_port_data:
        print("Значения Unit/Порт не найдены на странице")
        return
    print("="*60)
    print("РЕЗУЛЬТАТЫ ПОИСКА И ОБРАБОТКИ UNIT/ПОРТ")
    print("="*60)
    for i, data in enumerate(unit_port_data, 1):
        if 'clean_match' in data and data['clean_match'] != data['original']:
            break
    # # Сохраняем переменные в файл
    with open("vars.pkl", "wb") as f:
        pickle.dump({"ip_address" : data['ip_address'], "port_number": data['port_number']}, f)
    print(f"IP = {data['ip_address']}")
    print(f"Порт = {data['port_number']}")  

def display_data_results(data_data):
    if not data_data:
        print("\n" + "="*60)
        print("РЕЗУЛЬТАТЫ ПОИСКА КВАРТИР/ПОМЕЩЕНИЙ")
        print("="*60)
        print("Номера квартир/помещений не найдены")
        return
    print("="*60)
    print("РЕЗУЛЬТАТЫ ПОИСКА ОСНОВНОЙ ИНФОРМАЦИИ")
    print("="*60)
    
    configs = [
        {'type': 'квартира', 'title': 'Квартира', 'prefix': 'Номер квартиры'},
        {'type': 'помещение', 'title': 'Помещение', 'prefix': 'Номер помещения'},
        {'type': 'Отключение', 'title': 'Отключение', 'prefix': 'Действие'},
        {'type': 'по заявлению', 'title': 'Причина', 'prefix': 'Причина'},
        {'type': 'Дата выполнения', 'title': 'Дата выполнения', 'prefix': 'Дата выполнения'}
    ]
    for config in configs:
        items = [f for f in data_data if f['type'] == config['type']]
        if items:
            for i, item in enumerate(items, 1):
                print(f"{config['prefix']}: {item['number']}")
        else:
            print(f"{config['title']}: None")
    print("="*60)

def main():
    username = "USERNAME" #USERNAME
    password = "PASSWORD" #PASSWORD
    print("\n\n" + "=" * 60)
    print("ВВЕДИТЕ ДАННЫЕ НАРЯДА:")
    print("=" * 60)
    project_id = get_input_with_default("ID наряда")
    # Создаем экземпляр аутентификатора
    crm = CRMAuthenticator("https://xxx.yyy/")
    # Выполняем вход
    print("="*60)
    print("ВЫПОЛНЕНИЕ ВХОДА В СИСТЕМУ")
    print("="*60)
    if not crm.login(username, password):
        print("\nНе удалось выполнить вход. Завершение работы.")
        return 1
    print(f"\n{crm.get_session_info()}")
    success, found_details, unit_port_data, data_data = crm.navigate_to_project(project_id) #, search_text)
    # Отображаем результаты поиска Unit/Порт
    display_unit_port_results(unit_port_data)
    # Отображаем результаты поиска квартир/помещений
    display_data_results(data_data)

if __name__ == "__main__":    
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nРабота прервана пользователем.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nКритическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
