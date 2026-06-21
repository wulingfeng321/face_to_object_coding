import random
from playcard import make_deck

# from userlog import add_log_entry

CARD_VALUES = {
    'A': 11,
    '2': 2,
    '3': 3,
    '4': 4,
    '5': 5,
    '6': 6,
    '7': 7,
    '8': 8,
    '9': 9,
    'T': 10,
    'J': 10,
    'Q': 10,
    'K': 10,
}


def calculate_hand_value(hand):
    # Calculate the value of a hand, considering Aces as 1 or 11.
    value, aces = 0, 0
    for card in hand:
        rank = card[0]
        value += CARD_VALUES[rank]
        aces += rank == 'A'

    # Adjust for Aces if needed
    while value > 21 and aces:
        value -= 10
        aces -= 1

    return value


# [修改] 新增辅助函数：判断是否为自然Blackjack（前两张牌为A+10点牌）
def is_natural_blackjack(hand):
    """检查是否为自然Blackjack（A + 10点牌）"""
    if len(hand) != 2:
        return False
    ranks = [card[0] for card in hand]
    return ('A' in ranks and any(r in ranks for r in ['T', 'J', 'Q', 'K']))


def new_game(session):
    # Create a standard deck of 52 cards
    session_id = session.get('session_id', '')
    deck = make_deck()
    random.shuffle(deck)
    card1, card2, card3 = deck.pop(), deck.pop(), deck.pop()
    player_hand = [card1, card3]
    # [修改] 欧式规则：庄家只发一张明牌，不发暗牌
    dealer_hand = [card2]
    dealer_value = calculate_hand_value(dealer_hand)
    player_value = calculate_hand_value(player_hand)

    # [修改] 欧式规则：不在游戏开始时检查庄家Blackjack
    # 庄家第二张牌保存在deck中，等玩家完成操作后再发
    session['game_state'] = {
        'deck': deck,
        'dealer_hand': dealer_hand,
        'player_hand': player_hand,
        'dealer_value': dealer_value,
        'player_value': player_value,
        'message': None,
        'message_class': '',
    }


def game_update(session, action):
    game_state = session.get('game_state', {})
    if not game_state:
        return new_game(session)

    session_id = session.get('session_id', '')
    deck = game_state['deck']
    dealer_hand = game_state['dealer_hand']
    player_hand = game_state['player_hand']

    if action == 'hit':
        # Deal a card to the player
        card = deck.pop()
        player_hand.append(card)
        player_value = calculate_hand_value(player_hand)
        game_state['player_value'] = player_value

        # Check if player busts
        if player_value > 21:
            game_state['dealer_value'] = calculate_hand_value(dealer_hand)
            game_state['message'] = '你爆牌了！庄家获胜。'
            game_state['message_class'] = 'lose-message'

    elif action == 'stand':
        # [修改] 欧式规则：玩家停牌后，庄家才抽取第二张牌
        player_value = game_state['player_value']

        # 庄家抽取第二张牌
        card = deck.pop()
        dealer_hand.append(card)
        dealer_value = calculate_hand_value(dealer_hand)

        # [修改] 欧式规则：检查庄家前两张牌是否为自然Blackjack
        if is_natural_blackjack(dealer_hand):
            # 庄家是自然Blackjack
            # 检查玩家是否也是自然Blackjack（前两张牌）
            if is_natural_blackjack(player_hand):
                game_state['message'] = '双方都是Blackjack，平局！'
                game_state['message_class'] = 'tie-message'
            else:
                # 即使玩家总点数为21（由3张以上牌组成），也输给庄家的自然Blackjack
                game_state['message'] = '庄家Blackjack获胜！'
                game_state['message_class'] = 'lose-message'
        else:
            # 庄家不是自然Blackjack，按原有规则继续要牌
            while dealer_value < 17:
                card = deck.pop()
                dealer_hand.append(card)
                dealer_value = calculate_hand_value(dealer_hand)

            # Determine the winner
            if dealer_value > 21:
                game_state['message'] = '庄家爆牌！你获胜！'
                game_state['message_class'] = 'win-message'
            elif dealer_value > player_value:
                game_state['message'] = '庄家获胜！'
                game_state['message_class'] = 'lose-message'
            elif dealer_value < player_value:
                game_state['message'] = '你获胜！'
                game_state['message_class'] = 'win-message'
            else:
                game_state['message'] = '平局！'
                game_state['message_class'] = 'tie-message'

        game_state['dealer_value'] = calculate_hand_value(dealer_hand)

    else:
        return

    # game state has changed itself so tell session it has changed
    session.modified = True
