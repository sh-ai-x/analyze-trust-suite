"""Stage 4 — EDA for Titanic survival prediction.

Loads data/raw/titanic.csv and prints:
  - dataset shape
  - missing-value counts per column
  - overall survival rate
  - survival rate by Sex, Pclass, Embarked, age bins (child<16 vs adult),
    and family size (SibSp + Parch).
"""
import pandas as pd

DATA = "data/raw/titanic.csv"


def main() -> None:
    df = pd.read_csv(DATA)

    print("=" * 60)
    print("DATASET SHAPE:", df.shape)
    print("=" * 60)

    print("\nMISSING-VALUE COUNTS PER COLUMN:")
    print(df.isna().sum().to_string())

    overall = df["Survived"].mean()
    print(f"\nOVERALL SURVIVAL RATE: {overall:.4f} "
          f"({df['Survived'].sum()}/{len(df)})")

    def rate_by(col):
        g = df.groupby(col)["Survived"].agg(["mean", "count"])
        print(f"\nSURVIVAL RATE BY {col}:")
        for idx, row in g.iterrows():
            print(f"  {col}={idx!s:<12} rate={row['mean']:.4f}  n={int(row['count'])}")

    rate_by("Sex")
    rate_by("Pclass")
    rate_by("Embarked")

    # Age bins: child (<16) vs adult (>=16). Rows with missing Age excluded.
    df_age = df.dropna(subset=["Age"]).copy()
    df_age["AgeGroup"] = (df_age["Age"] < 16).map({True: "child(<16)", False: "adult(>=16)"})
    g = df_age.groupby("AgeGroup")["Survived"].agg(["mean", "count"])
    print("\nSURVIVAL RATE BY AGE GROUP (Age known):")
    for idx, row in g.iterrows():
        print(f"  {idx:<12} rate={row['mean']:.4f}  n={int(row['count'])}")

    # Family size
    df["FamilySize"] = df["SibSp"] + df["Parch"] + 1
    g = df.groupby("FamilySize")["Survived"].agg(["mean", "count"])
    print("\nSURVIVAL RATE BY FAMILY SIZE (SibSp+Parch+1):")
    for idx, row in g.iterrows():
        print(f"  FamilySize={idx:<3} rate={row['mean']:.4f}  n={int(row['count'])}")

    df["IsAlone"] = (df["FamilySize"] == 1).astype(int)
    g = df.groupby("IsAlone")["Survived"].agg(["mean", "count"])
    print("\nSURVIVAL RATE BY IsAlone:")
    for idx, row in g.iterrows():
        label = "alone" if idx == 1 else "with-family"
        print(f"  {label:<12} rate={row['mean']:.4f}  n={int(row['count'])}")


if __name__ == "__main__":
    main()
