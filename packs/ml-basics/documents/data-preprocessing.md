# Data Preprocessing

Data preprocessing is the process of transforming raw data into a clean, structured format suitable for machine learning algorithms. It is often the most time-consuming step in a machine learning project, but also one of the most important — poor data quality leads to poor model performance.

## Handling Missing Values

Real-world datasets frequently contain missing values. Common strategies include:

- **Deletion**: Remove rows or columns with missing values. Simple but can lose valuable data.
- **Mean/Median imputation**: Replace missing numerical values with the column mean or median.
- **Mode imputation**: Replace missing categorical values with the most frequent category.
- **Model-based imputation**: Use algorithms like k-nearest neighbors to predict missing values based on other features.

## Feature Scaling

Many algorithms perform better when features are on a similar scale:

- **Normalization (Min-Max scaling)**: Rescales values to a range of [0, 1]. Useful when the distribution is not Gaussian.
- **Standardization (Z-score scaling)**: Centers values around zero with unit variance. Preferred when the data follows a normal distribution.
- **Robust scaling**: Uses the median and interquartile range, making it resistant to outliers.

## Encoding Categorical Variables

Machine learning algorithms require numerical inputs:

- **Label encoding**: Assigns each category an integer (e.g., red=0, blue=1, green=2). Suitable for ordinal data.
- **One-hot encoding**: Creates a binary column for each category. Avoids implying ordinal relationships.
- **Target encoding**: Replaces categories with the mean of the target variable. Can be powerful but risks overfitting.

## Feature Engineering

Creating new features from existing data can significantly improve model performance:

- **Polynomial features**: Create interaction terms and powers of existing features.
- **Binning**: Convert continuous variables into discrete bins (e.g., age groups).
- **Log transformation**: Reduce skewness in highly skewed distributions.
- **Date/time features**: Extract day of week, month, hour, or season from timestamps.

## Train-Test Split

Always split data before any preprocessing that uses statistics from the data (like mean for imputation). A typical split is 80% training and 20% testing. For more robust evaluation, use k-fold cross-validation, which rotates the test set across k different subsets of the data.
