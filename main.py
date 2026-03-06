import time
import os
import logging

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException


# ==============================
# LOAD ENVIRONMENT VARIABLE
# ==============================

USERNAME = os.getenv("PENS_USERNAME")
PASSWORD = os.getenv("PENS_PASSWORD")

if not USERNAME or not PASSWORD:
    raise ValueError("PENS_USERNAME dan PENS_PASSWORD belum diisi pada environment variable")


# ==============================
# KONFIGURASI
# ==============================

URL_LOGIN = "https://login.pens.ac.id/cas/login?service=http%3A%2F%2Fethol.pens.ac.id%2Fcas%2F"
URL_DAFTAR_KULIAH = "https://ethol.pens.ac.id/mahasiswa/matakuliah"

INTERVAL_CEK = 900  # 15 menit


# ==============================
# LOGGING
# ==============================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# ==============================
# SETUP CHROME
# ==============================

def setup_driver():

    options = webdriver.ChromeOptions()

    options.binary_location = "/usr/bin/google-chrome"

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    options.add_argument("--disable-extensions")
    options.add_argument("--disable-setuid-sandbox")

    options.add_argument("--disable-images")
    options.add_argument("--blink-settings=imagesEnabled=false")

    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-background-timer-throttling")

    options.add_argument("--disable-sync")
    options.add_argument("--disable-translate")

    options.add_argument("--no-zygote")

    options.add_argument("--log-level=3")

    service = Service()

    driver = webdriver.Chrome(service=service, options=options)

    return driver


# ==============================
# CEK PRESENSI
# ==============================

def cek_semua_absen():

    driver = None

    try:

        logging.info("Memulai browser...")

        driver = setup_driver()

        wait = WebDriverWait(driver, 120)

        logging.info("Membuka halaman login...")

        driver.get(URL_LOGIN)

        wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(USERNAME)

        driver.find_element(By.ID, "password").send_keys(PASSWORD)

        driver.find_element(By.NAME, "submit").click()

        logging.info("Menunggu login berhasil...")

        wait.until(EC.url_contains("ethol.pens.ac.id/mahasiswa/beranda"))

        logging.info("Login berhasil")

        time.sleep(2)

        logging.info("Membuka halaman matakuliah")

        driver.get(URL_DAFTAR_KULIAH)

        wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//label[contains(text(),'Tahun Ajaran')]")
            )
        )

        logging.info("Mengambil daftar mata kuliah")

        matkul_elements = wait.until(
            EC.presence_of_all_elements_located(
                (By.XPATH, "//span[contains(@class,'card-title-mobile')]")
            )
        )

        daftar_matkul = sorted(
            list({x.text.strip() for x in matkul_elements if x.text.strip()})
        )

        if not daftar_matkul:
            logging.warning("Tidak ada mata kuliah ditemukan")
            return

        logging.info(f"Matkul ditemukan: {', '.join(daftar_matkul)}")

        for matkul in daftar_matkul:

            logging.info(f"Cek presensi: {matkul}")

            try:

                tombol_akses = wait.until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            f"//div[contains(@class,'card-matkul') and .//span[normalize-space()='{matkul}']]//button[contains(.,'Akses Kuliah')]"
                        )
                    )
                )

                driver.execute_script("arguments[0].click();", tombol_akses)

                wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//button[normalize-space(span)='Aturan Presensi']")
                    )
                )

                time.sleep(1)

                tombol_presensi = driver.find_element(
                    By.XPATH,
                    "//button[normalize-space(span)='Presensi' and not(@disabled)]"
                )

                if tombol_presensi.is_displayed() and tombol_presensi.is_enabled():

                    tombol_presensi.click()

                    logging.warning(f"PRESENSI BERHASIL: {matkul}")

                    return

                else:

                    logging.info("Presensi masih tertutup")

            except NoSuchElementException:

                logging.info("Presensi belum tersedia")

            except TimeoutException:

                logging.warning("Halaman timeout")

            except Exception as e:

                logging.error(f"Error cek {matkul}: {e}")

            driver.get(URL_DAFTAR_KULIAH)

            wait.until(
                EC.visibility_of_element_located(
                    (By.XPATH, "//label[contains(text(),'Tahun Ajaran')]")
                )
            )

            time.sleep(1)

    except WebDriverException as e:

        logging.critical(f"Gagal menjalankan Chrome: {e}")

    except Exception as e:

        logging.critical(f"Error tidak terduga: {e}")

    finally:

        if driver:

            logging.info("Menutup browser")

            driver.quit()


# ==============================
# LOOP UTAMA
# ==============================

if __name__ == "__main__":

    while True:

        logging.info("Memulai siklus pengecekan")

        cek_semua_absen()

        logging.info(f"Siklus selesai. Menunggu {INTERVAL_CEK/60:.0f} menit")

        time.sleep(INTERVAL_CEK)
