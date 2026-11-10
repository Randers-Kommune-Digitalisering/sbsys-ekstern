# SBSYS Ekstern

**NB:** Der er ingen integration mellem SD (Silkeborg Data) og Signatur. Appen journaliserer kun filer i SBSYS.

En Python-app, der giver Signatur et Keycloak-beskyttet API til at uploade PDF-dokumenter til personalesager i SBSYS. Uploadede dokumenter behandles i baggrunden, og deres status kan hentes via API'et.

## Flow

1. Signatur sender en PDF og oplysninger om ansættelse og institution til API'et. Uploaden valideres og gemmes med et ID.
2. En baggrundsproces finder den tilhørende personalesag i SBSYS. Hvis sagen mangler, bruger processen RPA til at slå ansættelsen op i SD Personaleweb og udløse oprettelsen af personalesagen, før den forsøger at finde sagen igen. Derefter journaliseres dokumentet i SBSYS.
3. Signatur kan hente uploadens status via API'et med ID'et for at se, om behandlingen lykkedes.
