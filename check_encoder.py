from joblib import load

encoder = load("models/label_encoder.pkl")

print("Classes:")
print(encoder.classes_)

print("\nTest:")

for i in range(len(encoder.classes_)):
    print(i, "->", encoder.inverse_transform([i])[0])
