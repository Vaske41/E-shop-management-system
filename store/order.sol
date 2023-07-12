pragma solidity ^0.8.2;

contract Payment {
	address payable courier;
	address payable owner;
	address customer;

	bool paid = false;
	bool picked = false;
	bool delivered = false;


	modifier is_customer() {
		require(msg.sender == customer, "Invalid customer account.");
		_;
	}

	modifier is_paid() {
		require(paid, "Transfer not complete.");
		_;
	}

	modifier not_paid() {
		require(!paid, "Transfer already complete.");
		_;
	}

	modifier picked_up() {
		require(picked, "Delivery not complete.");
		_;
	}

	modifier not_picked_up(){
		require(!picked, "Already picked up.");
		_;
	}

	modifier not_delivered(){
		require(!delivered, "Already delivered");
		_;
	}

	constructor (address _customer) {
		owner = payable(msg.sender);
		customer = _customer;
	}

	function pay() external payable is_customer not_paid {
		paid = true;
	}

	function pick_up(address payable _courier) external is_paid not_picked_up {
		courier = _courier;
		picked = true;
	}

	function deliver() external is_customer picked_up not_delivered {
		uint amount = address(this).balance;
		owner.transfer(amount * 8 / 10);
		courier.transfer(amount * 2 / 10);
		delivered = true;
	}
}