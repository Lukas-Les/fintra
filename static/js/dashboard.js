function getUserIdentifier() {
  const cookieString = `; ${document.cookie}`;
  const parts = cookieString.split(`; email=`);
  if (parts.length === 2) {
    const value = parts.pop().split(";").shift();
    return value.replace(/^"|"$/g, "");
  }
}

function getBalance() {
  const balanceDisplay = document.getElementById("balance-display");
  if (!balanceDisplay) {
    console.error("Element with id 'balance-display' not found.");
    return;
  }
  fetch("/balance")
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      const balanceValue = data.balance;
      balanceDisplay.innerHTML = `<h3 class="text-success">${balanceValue}</h3>`;
    })
    .catch((error) => {
      console.error("Error fetching balance:", error);
      balanceDisplay.innerHTML = `<p class="text-danger">Failed to load balance.</p>`;
    });
}
function submitTransaction() {
  const submitTransactionForm = document.getElementById(
    "submit-transaction-form",
  );

  if (submitTransactionForm) {
    const formData = new FormData(submitTransactionForm);
    const transactionData = Object.fromEntries(formData.entries());
    const actionDisplay = document.getElementById("action-display");

    fetch("/transaction", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(transactionData),
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        console.log("Transaction submitted successfully");
        submitTransactionForm.reset(); // Clear the form
        if (actionDisplay) {
          actionDisplay.innerHTML = `<div class="alert alert-success" role="alert">Transaction submitted successfully!</div>`;
        }
      })
      .catch((error) => {
        console.error("Error submitting transaction:", error);
        if (actionDisplay) {
          actionDisplay.innerHTML = `<div class="alert alert-danger" role="alert">Error: ${error.message || "Failed to submit transaction."}</div>`;
        }
      });
  } else {
    console.log("Form not found.");
  }
  getBalance();
}

const submitTransactionForm = document.getElementById(
  "submit-transaction-form",
);
submitTransactionForm.addEventListener("submit", function (event) {
  // Prevent the default form submission, which causes a page reload
  event.preventDefault();

  submitTransaction();
});

const fetchBalanceButton = document.querySelector("button#balance-display-btn");
if (fetchBalanceButton) {
  fetchBalanceButton.onclick = getBalance;
}
window.onload = function () {
  const displayElement = document.getElementById("username-display");
  const username = getUserIdentifier();
  displayElement.textContent = username;
  getBalance();
};
