pragma solidity ^0.6.3;


contract Survey {

    string public survey_title;
    string public survey_data;
    uint public survey_count;
    uint public upper_limit;
    uint public reward;

    bool ended = false;
    // 调查的主持人（调查发起人）
    address payable public chairperson;
    // 总的奖励
    uint public reward_totle;
    // 答卷人
    struct Participant {
        // uint weight;
        bool voted;
        string answer_data;
    }
    // 答卷人地址和状态的对应关系
    mapping(address => Participant) public participants;

    // 事件是能方便地调用以太坊虚拟机日志功能的接口，这里记录答卷记录
    event AnswerEnded(address participant, uint reward_left);

    // 初始化合约，给定调查标题，问卷内容数据，问卷份数，单份的奖励
    constructor(string memory title, string memory survey_ipfs, uint limit, uint _reward) public payable {
        // 需要合约的余额足够支付预计支付的总金额
        require(msg.value >= limit*_reward);
        chairperson = msg.sender;
        reward_totle = msg.value;
        survey_title = title;
        survey_data = survey_ipfs;
        upper_limit = limit;
        reward = _reward;
        survey_count = 0;
    }

    // 答卷人回答问卷，成功则获得奖励
    function answer(string memory survey_ipfs, string memory answer_ipfs) public {
        // 取得答卷人的状态数据
        Participant storage sender = participants[msg.sender];
        require(!sender.voted, "Already participated.");
        require(survey_count<upper_limit, "Survey is full of participants");

        // 更新答卷人状态数据
        sender.voted = true;
        sender.answer_data = answer_ipfs;
        survey_data = survey_ipfs;
        // 更新成功答卷份数
        survey_count += 1;

        emit AnswerEnded(msg.sender, reward_totle-reward*survey_count);
        // 发送答卷人所得奖励
        msg.sender.transfer(reward);
    }

    // 结束答卷并取回剩余奖励金额
    function surveyEnd() public {
        require(!ended);
        require(msg.sender == chairperson);

        ended = true;

        chairperson.transfer(reward_totle-reward*survey_count);
    }

}

