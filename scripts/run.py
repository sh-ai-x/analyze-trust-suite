"""Stage 5 — modeling loop for Titanic survival prediction.

Fixed random_state=42, 5-fold StratifiedKFold. Reports mean +/- std accuracy and
delta vs. previous best for each iteration.

  iter0: majority-class baseline (everyone dies)
  iter1: sex-only rule (female => survive)
  iter2: LogisticRegression on basic features (Pipeline: impute + one-hot + scale)
  iter3: RandomForestClassifier on the same basic features
  iter4: HistGradientBoosting with engineered features
         (FamilySize, IsAlone, Title, AgeBin, FareBin)
"""
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

SEED = 42
DATA = "data/raw/titanic.csv"
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)


def load():
    return pd.read_csv(DATA)


def report(name, scores, best_so_far):
    mean, std = scores.mean(), scores.std()
    delta = mean - best_so_far if best_so_far is not None else 0.0
    arrow = "(baseline)" if best_so_far is None else f"delta vs best={delta:+.4f}"
    print(f"{name:<42} CV acc = {mean:.4f} +/- {std:.4f}   {arrow}")
    return mean, std, delta


def engineer(df):
    df = df.copy()
    df["FamilySize"] = df["SibSp"] + df["Parch"] + 1
    df["IsAlone"] = (df["FamilySize"] == 1).astype(int)
    df["Title"] = (
        df["Name"].str.extract(r",\s*([^\.]+)\.", expand=False).str.strip()
    )
    rare = ~df["Title"].isin(["Mr", "Mrs", "Miss", "Master"])
    df.loc[rare, "Title"] = "Rare"
    df["AgeBin"] = pd.cut(
        df["Age"], bins=[-1, 16, 32, 48, 64, 200],
        labels=["child", "young", "mid", "senior", "old"],
    ).astype("object").fillna("unknown")
    df["FareBin"] = pd.qcut(df["Fare"], q=4, labels=["q1", "q2", "q3", "q4"]).astype("object")
    return df


def main():
    df = load()
    y = df["Survived"].values
    results = {}
    best = None

    print("=" * 70)
    print("MODELING LOOP — 5-fold StratifiedKFold, random_state=42")
    print("=" * 70)

    # iter0: majority class (everyone dies -> predict 0)
    maj = (df["Survived"] == 0).mean()
    print(f"{'iter0 majority-class (all die)':<42} CV acc = {maj:.4f} +/- 0.0000   (baseline)")
    results["iter0"] = (maj, 0.0, 0.0)
    best = maj

    # iter1: sex-only rule (female -> survive). Evaluated as fold-wise accuracy.
    pred_sex = (df["Sex"] == "female").astype(int).values
    fold_acc = []
    for _, test_idx in cv.split(df, y):
        fold_acc.append((pred_sex[test_idx] == y[test_idx]).mean())
    sex_scores = np.array(fold_acc)
    mean, std, delta = report("iter1 sex-only rule (female=survive)", sex_scores, best)
    results["iter1"] = (mean, std, delta)
    best = max(best, mean)

    # Basic feature set for iter2 / iter3
    basic_num = ["Age", "Fare", "SibSp", "Parch"]
    basic_cat = ["Pclass", "Sex", "Embarked"]
    X_basic = df[basic_num + basic_cat]

    pre_basic = ColumnTransformer([
        ("num", Pipeline([
            ("imp", SimpleImputer(strategy="median")),
            ("sc", StandardScaler()),
        ]), basic_num),
        ("cat", Pipeline([
            ("imp", SimpleImputer(strategy="most_frequent")),
            ("oh", OneHotEncoder(handle_unknown="ignore")),
        ]), basic_cat),
    ])

    # iter2: LogisticRegression
    lr = Pipeline([("pre", pre_basic),
                   ("clf", LogisticRegression(max_iter=1000, random_state=SEED))])
    s = cross_val_score(lr, X_basic, y, cv=cv, scoring="accuracy")
    mean, std, delta = report("iter2 LogisticRegression (basic feats)", s, best)
    results["iter2"] = (mean, std, delta)
    best = max(best, mean)

    # iter3: RandomForest
    rf = Pipeline([("pre", pre_basic),
                   ("clf", RandomForestClassifier(n_estimators=300, random_state=SEED))])
    s = cross_val_score(rf, X_basic, y, cv=cv, scoring="accuracy")
    mean, std, delta = report("iter3 RandomForest (basic feats)", s, best)
    results["iter3"] = (mean, std, delta)
    best = max(best, mean)

    # iter4: HistGradientBoosting + engineered features
    dfe = engineer(df)
    eng_num = ["Age", "Fare", "SibSp", "Parch", "FamilySize", "IsAlone"]
    eng_cat = ["Pclass", "Sex", "Embarked", "Title", "AgeBin", "FareBin"]
    X_eng = dfe[eng_num + eng_cat]

    pre_eng = ColumnTransformer([
        ("num", SimpleImputer(strategy="median"), eng_num),
        ("cat", Pipeline([
            ("imp", SimpleImputer(strategy="most_frequent")),
            ("oh", OneHotEncoder(handle_unknown="ignore")),
        ]), eng_cat),
    ])
    hgb = Pipeline([("pre", pre_eng),
                    ("clf", HistGradientBoostingClassifier(random_state=SEED))])
    s = cross_val_score(hgb, X_eng, y, cv=cv, scoring="accuracy")
    mean, std, delta = report("iter4 HistGradientBoosting (engineered)", s, best)
    results["iter4"] = (mean, std, delta)
    best_iter4 = mean
    best = max(best, mean)

    # Determine best model
    model_iters = {k: v for k, v in results.items() if k not in ("iter0",)}
    best_name = max(model_iters, key=lambda k: model_iters[k][0])
    print("\n" + "=" * 70)
    print(f"BEST MODEL: {best_name}  "
          f"(CV acc = {results[best_name][0]:.4f} +/- {results[best_name][1]:.4f})")
    print("=" * 70)

    # Feature importances of the engineered HGB model (permutation-free proxy:
    # fit RandomForest on engineered feats to get interpretable importances since
    # HGB has no native importances). We report RF-on-engineered importances.
    rf_eng = Pipeline([("pre", pre_eng),
                       ("clf", RandomForestClassifier(n_estimators=300, random_state=SEED))])
    rf_eng.fit(X_eng, y)
    ohe = rf_eng.named_steps["pre"].named_transformers_["cat"].named_steps["oh"]
    feat_names = list(eng_num) + list(ohe.get_feature_names_out(eng_cat))
    importances = rf_eng.named_steps["clf"].feature_importances_
    order = np.argsort(importances)[::-1][:8]
    print("\nTOP 8 FEATURE IMPORTANCES (RandomForest on engineered features):")
    for i in order:
        print(f"  {feat_names[i]:<20} {importances[i]:.4f}")

    # Logistic regression coefficients (iter2) for linear interpretation
    lr.fit(X_basic, y)
    ohe2 = lr.named_steps["pre"].named_transformers_["cat"].named_steps["oh"]
    lr_names = list(basic_num) + list(ohe2.get_feature_names_out(basic_cat))
    coefs = lr.named_steps["clf"].coef_[0]
    order2 = np.argsort(np.abs(coefs))[::-1][:8]
    print("\nTOP 8 LOGISTIC-REGRESSION COEFFICIENTS (iter2, by |coef|):")
    for i in order2:
        print(f"  {lr_names[i]:<20} {coefs[i]:+.4f}")


if __name__ == "__main__":
    main()
