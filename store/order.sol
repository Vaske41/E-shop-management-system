pragma solidity ^0.8.2;

contract Purchase {
	address payable courier = payable (address(0));
	address payable owner;
	address customer;

	bool paid = false;
    bool picked = false;
	bool delivered = false;

	modifier picked_up() {
		require(picked, "No one picked up.");
		_;
	}

	modifier only_customer() {
		require(msg.sender == customer, "Invalid customer account.");
		_;
	}

	modifier already_payed() {
		require(paid, "Transfer not complete.");
		_;
	}

	modifier not_payed() {
		require(!paid, "Transfer already complete.");
		_;
	}

	modifier not_picked() {
		require(!picked, "Delivery not complete.");
		_;
	}

	modifier not_delivered() {
        require(!delivered, "Contract closed.");
		_;
	}

	constructor (address _customer) {
		owner = payable(msg.sender);
		customer = _customer;
	}

	function pay() external payable only_customer not_payed {
		paid = true;
	}

	function get_order_courier(address payable _courier) external already_payed not_picked {
		courier = _courier;
	}

	function deliver() external only_customer picked_up not_delivered {
		delivered = true;

		uint amount = address(this).balance;
		owner.transfer(amount * 8 / 10);
		courier.transfer(amount * 2 / 10);
	}
}