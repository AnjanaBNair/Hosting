from matplotlib import pyplot as plt
import pandas as pd
import seaborn as sns
import joblib
from sklearn.feature_selection import chi2
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score, train_test_split

def load_data():
    try:
        courses_df = pd.read_csv('course_synthetic.csv')
        enrollments_df = pd.read_csv('enrollment_synthetic.csv')
        print("Courses DataFrame: \n", courses_df.head())
        print("Enrollments DataFrame:\n", enrollments_df.head())
        return courses_df, enrollments_df
    except Exception as e:
        print("Error loading data:", str(e))
        raise e 
def prepare_data(enrollments_df):
    pivot_df = enrollments_df.pivot_table(index='student_id', columns='course_id', aggfunc='size', fill_value=0)
    X = pivot_df.values
    y = (X > 0).astype(int)
    print(f'Prepared data with shapes: X={X.shape}, y={y.shape}')
    return pivot_df, X, y
def chi_square_test(X, y):
    chi2_stats, p_values = chi2(X, y)
    chi2_df = pd.DataFrame({
        'Feature': range(X.shape[1]),
        'Chi2 Stat': chi2_stats,
        'p-value': p_values})
    return chi2_df
def train_and_evaluate_model(X_train, y_train, X_test, y_test):
    model = RandomForestClassifier(n_estimators=50, max_depth=8, random_state=42) 
    cv_scores = cross_val_score(model, X_train, y_train, cv=5)
    print(f"Cross-Validation Accuracy Scores: {cv_scores}")
    print(f"Mean CV Accuracy: {cv_scores.mean() * 100:.2f}%")
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred)
    print(f'Model Accuracy: {accuracy * 100:.2f}%')
    chi2_df = chi_square_test(X_train, y_train)
    print("Chi-Square Test Results:\n", chi2_df)
    plot_feature_importance(model, X_train)
    return model
def plot_feature_importance(model, X_train):
    importances = model.feature_importances_
    sorted_indices = importances.argsort()[::-1]
    sorted_importances = importances[sorted_indices]
    feature_labels = [f"Feature {i}" for i in sorted_indices]
    plt.figure(figsize=(10, 6))
    sns.barplot(x=sorted_importances, y=feature_labels, palette='viridis')
    plt.xlabel('Feature Importance')
    plt.ylabel('Features')
    plt.title('Feature Importance in Course Recommendation')
    plt.show()
def save_model(model):
    joblib.dump(model, 'course_recommendation_model.pkl')
    print('Model saved as course_recommendation_model.pkl')
def initial_training():
    courses_df, enrollments_df = load_data()
    pivot_df, X, y = prepare_data(enrollments_df)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = train_and_evaluate_model(X_train, y_train, X_test, y_test)
    save_model(model)
if __name__ == "__main__":
    initial_training()
