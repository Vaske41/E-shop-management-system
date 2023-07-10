pragma solidity ^0.8.4;

contract Order{

    address payable public owner;
    address payable public courier;
    address payable public customer;

    bool customerPaid = false;
    bool courierPickedUp = false;
    bool delivired = false;

    modifier isOnlyCreated(){
        require(customerPaid==false, "Transfer already complete.");
        _;
    }

    modifier isCustomer() {
        require(msg.sender == customer, "Invalid customer account.");
        _;
    }

    modifier isForCourier() {
        require(customerPaid==true, "Transfer not complete.");
        _;
    }

    modifier isForDelivery(){
        require(courierPickedUp==true, "Delivery not complete.");
        _;
    }

    constructor(address payable c) payable public{
        owner = payable (msg.sender);
        customer = c;

    }

    function pay() payable isCustomer isOnlyCreated public{
        customerPaid = true;
    }

    function pickUp(address payable c) isForCourier public{
        courier = c;
        courierPickedUp = true;
    }

    function delivered() isCustomer isForCourier isForDelivery public{
        uint amount = address(this).balance;
        owner.transfer(amount * 8 / 10);
        courier.transfer(amount * 2 / 10);
    }

}