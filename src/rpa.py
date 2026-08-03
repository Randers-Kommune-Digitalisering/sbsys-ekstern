import logging
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright
from config import SD_PERSONALESAG_ROBOT_USERNAME, SD_PERSONALESAG_ROBOT_PASSWORD


logger = logging.getLogger(__name__)


def playwright_sd_personalesag_files(input_strings, headless=True):
    """Local Playwright variant of browserless_sd_personalesag_files."""

    table_selector = '#psagform\\:sk\\:j_idt107\\:0\\:j_idt124\\:0\\:table1\\:table1_data'

    def process_rows(page):
        page.wait_for_timeout(3000)
        page.wait_for_selector(table_selector, timeout=3000)
        return page.evaluate(
            """
            (selector) => {
                const rows = document.querySelectorAll(`${selector} tr`);
                const rowData = [];
                rows.forEach((row) => {
                    const cells = row.querySelectorAll('td[role="gridcell"]');
                    if (cells.length > 0) {
                        const navn = cells[3] ? cells[3].innerText.trim() : '';
                        const arkivdato = cells[8] ? cells[8].innerText.trim() : '';
                        rowData.push({ navn, arkivdato });
                    }
                });
                return rowData;
            }
            """,
            table_selector,
        )

    def process_input_string(page, input_string, all_results):
        tags_input = page.locator('#tags')
        tags_input.wait_for()
        tags_input.click()
        tags_input.fill('')
        tags_input.type(input_string, delay=100)
        page.wait_for_timeout(500)

        try:
            page.wait_for_selector('.ui-menu-item', state='visible', timeout=5000)
        except PlaywrightTimeoutError:
            logger.info("No items found in dropdown menu for input: %s", input_string)
            return

        dropdown_count = page.locator('.ui-menu-item').count()
        if dropdown_count == 0:
            logger.info("No dropdown item found for input: %s", input_string)
            return

        for i in range(dropdown_count):
            dropdown_item_selector = f'li.ui-menu-item:nth-child({i + 1})'
            dropdown_text = page.locator(dropdown_item_selector).inner_text()

            page.wait_for_timeout(1500)
            page.wait_for_selector(dropdown_item_selector)
            page.wait_for_timeout(1500)
            page.click(dropdown_item_selector)

            page.wait_for_timeout(1500)
            page.goto(
                'https://www.silkeborgdata.dk/sdpw/faces/esdh/psag/PersonalesagLoader.xhtml?from=frontpage',
                wait_until='networkidle',
            )

            page.wait_for_selector('#psagform\\:sk\\:j_idt107\\:0\\:j_idt124\\:0\\:j_idt132')
            page.click('#psagform\\:sk\\:j_idt107\\:0\\:j_idt124\\:0\\:j_idt132')

            rows = process_rows(page)
            if len(rows) == 1:
                first_item = rows[0]
                if first_item.get('navn', '') == '' and first_item.get('arkivdato', '') == '':
                    rows = process_rows(page)

            all_results.append({'inputString': input_string, 'dropdownText': dropdown_text, 'result': rows})

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(30000)

        try:
            page.goto('https://sd.dk/start', wait_until='networkidle')
            page.wait_for_selector('#arbejdspladsButton', timeout=5000)
            page.click('#arbejdspladsButton')

            page.wait_for_selector('iframe')
            iframe_element = page.query_selector('iframe')
            iframe = iframe_element.content_frame() if iframe_element else None
            if iframe is None:
                raise RuntimeError('Could not access login iframe on sd.dk/start')

            iframe.wait_for_selector('#oiosaml-idp')
            value = iframe.evaluate(
                """
                () => {
                    const options = document.querySelectorAll('#oiosaml-idp option');
                    for (const option of options) {
                        if (option.textContent.trim() === 'Randers Kommune') {
                            return option.value;
                        }
                    }
                    return null;
                }
                """
            )

            if not value:
                raise RuntimeError("Could not find 'Randers Kommune' option in #oiosaml-idp")

            page.goto(f'https://sd.dk/{value}')
            page.wait_for_selector('#userNameInput')
            page.fill('#userNameInput', SD_PERSONALESAG_ROBOT_USERNAME)

            page.wait_for_selector('#passwordInput')
            page.fill('#passwordInput', SD_PERSONALESAG_ROBOT_PASSWORD)

            page.click('#submitButton')
            page.wait_for_timeout(1500)
            page.wait_for_function(
                """
                () => Array.from(document.querySelectorAll('div.product-title'))
                    .some((el) => el.textContent && el.textContent.trim() === 'Personaleweb')
                """,
                timeout=45000,
            )

            page.goto('https://www.silkeborgdata.dk/sdpw/', wait_until='networkidle')

            all_results = []
            for input_string in input_strings:
                process_input_string(page, input_string, all_results)

            return {
                'data': {
                    'allResults': all_results,
                },
                'type': 'application/json',
            }
        except Exception:
            raise
        finally:
            context.close()
            browser.close()


def playwright_sd_personalesag_exist(input_string, headless=True):
    """Local Playwright variant of browserless_sd_personalesag_exist."""
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright
    except ImportError as exc:
        raise ImportError("Playwright is not installed. Install it with: pip install playwright") from exc

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(30000)

        try:
            page.goto('https://sd.dk/start', wait_until='networkidle')
            page.wait_for_selector('#arbejdspladsButton', timeout=5000)
            page.click('#arbejdspladsButton')

            page.wait_for_selector('iframe')
            iframe_element = page.query_selector('iframe')
            iframe = iframe_element.content_frame() if iframe_element else None
            if iframe is None:
                raise RuntimeError('Could not access login iframe on sd.dk/start')

            iframe.wait_for_selector('#oiosaml-idp')
            value = iframe.evaluate(
                """
                () => {
                    const options = document.querySelectorAll('#oiosaml-idp option');
                    for (const option of options) {
                        if (option.textContent.trim() === 'Randers Kommune') {
                            return option.value;
                        }
                    }
                    return null;
                }
                """
            )

            if not value:
                raise RuntimeError("Could not find 'Randers Kommune' option in #oiosaml-idp")

            page.goto(f'https://sd.dk/{value}')
            page.wait_for_selector('#userNameInput')
            page.fill('#userNameInput', SD_PERSONALESAG_ROBOT_USERNAME)

            page.wait_for_selector('#passwordInput')
            page.fill('#passwordInput', SD_PERSONALESAG_ROBOT_PASSWORD)

            page.click('#submitButton')
            page.wait_for_timeout(1500)
            page.wait_for_function(
                """
                () => Array.from(document.querySelectorAll('div.product-title'))
                    .some((el) => el.textContent && el.textContent.trim() === 'Personaleweb')
                """,
                timeout=45000,
            )

            page.goto('https://www.silkeborgdata.dk/sdpw/', wait_until='networkidle')
            tags_input = page.locator('#tags')
            tags_input.wait_for()
            tags_input.click()
            tags_input.fill('')
            tags_input.type(input_string, delay=100)
            page.wait_for_timeout(500)

            try:
                page.wait_for_selector('.ui-menu-item', state='visible', timeout=5000)
            except PlaywrightTimeoutError:
                return {
                    'data': {
                        'success': False,
                        'msg': 'No dropdown item found.',
                    },
                    'type': 'application/json',
                }

            dropdown_count = page.locator('.ui-menu-item').count()
            if dropdown_count == 0:
                return {
                    'data': {
                        'success': False,
                        'msg': 'No dropdown item found.',
                    },
                    'type': 'application/json',
                }

            for i in range(dropdown_count):
                dropdown_item_selector = f'li.ui-menu-item:nth-child({i + 1})'

                page.wait_for_timeout(2500)
                page.wait_for_selector(dropdown_item_selector)
                page.wait_for_timeout(2500)
                page.click(dropdown_item_selector)

                page.wait_for_timeout(2500)
                page.goto(
                    'https://www.silkeborgdata.dk/sdpw/faces/esdh/psag/PersonalesagLoader.xhtml?from=frontpage',
                    wait_until='networkidle',
                )
                page.wait_for_selector('#sager')

                page_state = page.evaluate(
                    """
                    () => {
                        const collectTexts = (selector) => Array.from(document.querySelectorAll(selector))
                            .map((el) => (el.textContent || '').trim())
                            .filter(Boolean);

                        const errorSelectors = [
                            '.ui-messages-error',
                            '.ui-messages-error-summary',
                            '.ui-message-error',
                            '.ui-message-error-summary',
                            '[class*="error"]',
                        ];

                        const errorMessages = [...new Set(
                            errorSelectors.flatMap((selector) => collectTexts(selector))
                        )];

                        const personalesagFound = Array.from(document.querySelectorAll("[id^='psagform']"))
                            .some((el) => (el.textContent || '').trim() === 'Personalesag');

                        const bodyText = document.body ? document.body.innerText : '';
                        const genericErrorMatch = bodyText.match(
                            /(der opstod en fejl[^\n]*|adgang nægtet[^\n]*|ingen adgang[^\n]*|unexpected error[^\n]*)/i
                        );

                        return {
                            personalesagFound,
                            errorMessages,
                            genericError: genericErrorMatch ? genericErrorMatch[0].trim() : null,
                        };
                    }
                    """
                )

                success = page_state['personalesagFound'] and not page_state['errorMessages'] and not page_state['genericError']
                failure_msg = 'Did not find personalesag.'
                if page_state['errorMessages']:
                    failure_msg = page_state['errorMessages'][0]
                elif page_state['genericError']:
                    failure_msg = page_state['genericError']

                return {
                    'data': {
                        'success': success,
                        'msg': 'Personalesag found.' if success else failure_msg,
                    },
                    'type': 'application/json',
                }

            return {
                'data': {
                    'success': False,
                    'msg': 'No dropdown item found.',
                },
                'type': 'application/json',
            }
        except Exception:
            raise
        finally:
            context.close()
            browser.close()
