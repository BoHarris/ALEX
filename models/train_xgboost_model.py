import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import joblib
import os
import sys
import ast #pasring value_samples
import re #pattern matching

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.pii_features import extract_column_features

#Step 1: load the column level dataset
df = pd.read_csv("pii_column.csv")
df["parsed_values"] = df["value_samples"].apply(ast.literal_eval)

#step 2 map PII to numeric values
df["is_pii"] = df["pii"].map({"yes": 0, "no": 1}) #note 0 =PII

#Step 3: Extract features from column name
df = extract_column_features(df)

#feature engineering
def contains_dob_pattern(values):
    dob_re = re.compile(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})|(\d{4}[/-]\d{1,2}[/-]\d{1,2})")
    return any(bool(dob_re.search(str(v))) for v in values)

def contains_gender_term(values):
    gender_terms = {
        "abimegender", "adamasgender", "agender", "agenderflux", "agenderfluid", "alexigender", "aliusgender", "amaregender",
        "ambigender", "ambonec", "amicagender", "androgyne", "androgynous", "anesigender", "angenital", "anogender", "anongender",
        "antegender", "anxiegender", "apagender", "apconsugender", "aporagender", "astergender", "astralgender", "autigender",
        "autogender", "axigender", "bakla", "bigender", "binary", "biogender", "blurgender", "boyflux", "burstgender", "calabai",
        "calalai", "cassflux", "cassgender", "cavusgender", "cendgender", "ceterogender", "ceterofluid", "cisgender", "cis female",
        "cis male", "cis man", "cis woman", "cloudgender", "collgender", "colorgender", "commogender", "condigender", "deliciagender",
        "demiboy", "demifluid", "demiflux", "demigender", "demigirl", "demiguy", "demiman", "demiwoman", "domgender", "duragender",
        "egogender", "epicene", "esspigender", "exgender", "existigender", "fa'afafine", "femfluid", "femgender", "female", "female to male",
        "femme", "ftm", "fluidflux", "gemigender", "gender bender", "gender blank", "gender gifted", "genderfluid", "genderflow",
        "genderfuzz", "genderless", "gender neutral", "gender nonconforming", "genderpuck", "genderqueer", "gender questioning",
        "gender variant", "gender witched", "girlflux", "graygender", "healgender", "hijra", "intergender", "intersex", "ipsogender",
        "kathoey", "male", "male to female", "man", "man of trans experience", "māhū", "maverique", "meta-gender", "mirrorgender", "mtf",
        "muxe", "neutrois", "non-binary", "nonbinary", "non-binary transgender", "nullo", "omnigender", "other", "pangender",
        "person of transgendered experience", "polygender", "polyagender", "queer", "questioning", "sekhet", "third gender", "trans",
        "trans*", "trans female", "trans male", "trans man", "trans person", "trans woman", "transgender", "transgender female",
        "transgender male", "transgender man", "transgender person", "transgender woman", "transfeminine", "transmasculine",
        "transsexual", "transsexual female", "transsexual male", "transsexual man", "transsexual person", "transsexual woman",
        "travesti", "trigender", "tumtum", "two-spirit", "vakasalewalewa", "waria", "winkte", "woman", "woman of trans experience",
        "x-gender", "x-jendā", "xenogender"
    }
    return any(str(v).strip().lower() in gender_terms for v in values)

def contains_street_suffix(values):
    street_suffixes = {
        "alley", "aly", "annex", "anx", "arcade", "arc", "avenue", "ave", "bayou", "byu", "beach", "bch", "bend", "bnd", "bluff", "blf",
        "bluffs", "blfs", "bottom", "btm", "boulevard", "blvd", "branch", "br", "bridge", "brg", "brook", "brk", "brooks", "brks",
        "burg", "bg", "bypass", "byp", "camp", "cp", "canyon", "cyn", "cape", "cpe", "causeway", "cswy", "center", "ctr", "centers", "ctrs",
        "circle", "cir", "circles", "cirs", "cliff", "clf", "cliffs", "clfs", "club", "clb", "common", "cmn", "commons", "cmns", "corner", "cor",
        "corners", "cors", "course", "crse", "court", "ct", "courts", "cts", "cove", "cv", "coves", "cvs", "creek", "crk", "crescent", "cres",
        "crest", "crst", "crossing", "xing", "crossroad", "xrd", "curve", "curv", "dale", "dl", "dam", "dm", "divide", "dv", "drive", "dr",
        "drives", "drs", "estate", "est", "estates", "ests", "expressway", "expy", "extension", "ext", "extensions", "exts", "fall", "fall",
        "falls", "fls", "ferry", "fry", "field", "fld", "fields", "flds", "flat", "flt", "flats", "flts", "ford", "frd", "fords", "frds",
        "forest", "frst", "forge", "frg", "forges", "frgs", "fork", "frk", "forks", "frks", "fort", "ft", "freeway", "fwy", "garden", "gdn",
        "gardens", "gdns", "gateway", "gtwy", "glen", "gln", "glens", "glns", "green", "grn", "greens", "grns", "grove", "grv", "groves", "grvs",
        "harbor", "hbr", "harbors", "hbrs", "haven", "hvn", "heights", "hts", "highway", "hwy", "hill", "hl", "hills", "hls", "hollow", "holw",
        "inlet", "inlt", "island", "is", "islands", "iss", "isle", "isle", "junction", "jct", "junctions", "jcts", "key", "ky", "keys", "kys",
        "knoll", "knl", "knolls", "knls", "lake", "lk", "lakes", "lks", "land", "land", "landing", "lndg", "lane", "ln", "light", "lgt",
        "lights", "lgts", "loaf", "lf", "lock", "lck", "locks", "lcks", "lodge", "ldg", "loop", "loop", "mall", "mall", "manor", "mnr",
        "manors", "mnrs", "meadow", "mdw", "meadows", "mdws", "mews", "mews", "mill", "ml", "mills", "mls", "mission", "msn", "motorway", "mtwy",
        "mount", "mt", "mountain", "mtn", "mountains", "mtns", "neck", "nck", "orchard", "orch", "oval", "oval", "overpass", "opas", "park",
        "park", "parks", "par", "parkway", "pkwy", "parkways", "pkwys", "pass", "pass", "passage", "psge", "path", "path", "pike", "pike",
        "pine", "pne", "pines", "pnes", "place", "pl", "plain", "pln", "plains", "plns", "plaza", "plz", "point", "pt", "points", "pts",
        "port", "prt", "ports", "prts", "prairie", "pr", "radial", "radl", "ramp", "ramp", "ranch", "rnch", "rapid", "rpd", "rapids", "rpds",
        "rest", "rst", "ridge", "rdg", "ridges", "rdgs", "river", "riv", "road", "rd", "roads", "rds", "route", "rte", "row", "row", "rue",
        "rue", "run", "run", "shoal", "shl", "shoals", "shls", "shore", "shr", "shores", "shrs", "skyway", "skwy", "spring", "spg",
        "springs", "spgs", "spur", "spur", "spurs", "spurs", "square", "sq", "squares", "sqs", "station", "sta", "stravenue", "stra",
        "stream", "strm", "street", "st", "streets", "sts", "summit", "smt", "terrace", "ter", "throughway", "trwy", "trace", "trce",
        "track", "trak", "trafficway", "trfy", "trail", "trl", "trailer", "trlr", "tunnel", "tunl", "turnpike", "tpke", "underpass", "upas",
        "union", "un", "unions", "uns", "valley", "vly", "valleys", "vlys", "viaduct", "via", "view", "vw", "views", "vws", "village", "vlg",
        "villages", "vlgs", "ville", "vl", "vista", "vis", "walk", "walk", "walks", "walks", "wall", "wall", "way", "way", "ways", "ways",
        "well", "wl", "wells", "wls"
    }
    return any(str(v).strip().lower() in street_suffixes for v in values)

def contains_city_name(values):
    city_names = {"new york", "los angeles", "miami"}  # 👋 expand this later
    return any(str(v).lower() in city_names for v in values)

def contains_known_name(values):
    known_names = {"alice", "bob", "charlie", "john", "jane"}  # 👋 can use name lib later
    return any(any(word.lower() in known_names for word in str(v).split()) for v in values)

def contains_zip_code_pattern(values):
    zip_code_re = re.compile(r"\b\d{5}(?:-\d{4})?\b")
    return any(bool(zip_code_re.search(str(v))) for v in values)

def contains_phone_pattern(values):
    phone_patterns = [
        re.compile(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"),  # e.g., (123) 456-7890, 123-456-7890
        re.compile(r"\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")  # optional country code
    ]
    return any(any(p.search(str(v)) for p in phone_patterns) for v in values)


df["has_dob_pattern"] = df["parsed_values"].apply(contains_dob_pattern)
df["has_gender_term"] = df["parsed_values"].apply(contains_gender_term)
df["has_street_suffix"] = df["parsed_values"].apply(contains_street_suffix)
df["has_city_name"] = df["parsed_values"].apply(contains_city_name)
df["has_known_name"] = df["parsed_values"].apply(contains_known_name)
df["has_zip_pattern"] = df["parsed_values"].apply(contains_zip_code_pattern)
df["has_phone_pattern"] = df["parsed_values"].apply(contains_phone_pattern)

#existing features
features = ["length", "num_underscores", "num_digits", "has_at",
            "has_email_keyword", "pct_email_like", "pct_phone_like", 
            "pct_ssn_like", "pct_ip_like", "avg_digits_per_val","avg_val_len",  "has_dob_pattern",
    "has_gender_term", "has_street_suffix", "has_city_name", "has_known_name", "has_zip_pattern", "has_phone_pattern"]
print(f"Training on {len(df)} rows, {len(features)} features")
X=df[features]
y=df["is_pii"]

#Train/test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

#train model
model = xgb.XGBClassifier(use_label_encoder=False, eval_metric="logloss")
model.fit(X_train, y_train)

#Evaluate model
preds = model.predict(X_test)
print(classification_report(y_test, preds))
print(f"Accuracy: {accuracy_score(y_test, preds)}")

#Save model
joblib.dump(model, "xgboost_model.pkl")
print("Model saved to xgboost_model.pkl")