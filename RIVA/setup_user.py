
from getpass import getpass

from core.auth import create_user, user_exists


def main():
    """
    Početno stvaranje jedinog korisničkog računa RIVA-e.

    Koristi se samo prilikom prvog postavljanja aplikacije.
    Lozinka se unosi skriveno i ne zapisuje se u izvorni kod.
    """

    # Sprječavanje ponovnog stvaranja postojećeg računa.
    if user_exists():
        print("RIVA korisnički račun već postoji.")
        return

    print("=== RIVA | POČETNO POSTAVLJANJE ===")

    # Unos korisničkog imena.
    username = input("Korisničko ime: ").strip()

    # Siguran unos i potvrda lozinke.
    password = getpass("Lozinka (najmanje 10 znakova): ")
    confirmation = getpass("Ponovite lozinku: ")

    if password != confirmation:
        print("GREŠKA: Lozinke se ne podudaraju.")
        return

    try:
        # Stvaranje računa putem modula za autentifikaciju.
        create_user(username, password)
        print("USPJEH: RIVA korisnički račun je stvoren.")
    except ValueError as error:
        print(f"GREŠKA: {error}")


if __name__ == "__main__":
    main()
