import random
from playcard import make_deck, get_suit, get_rank_ace_high, SUITS, get_suit_name

# 游戏常量
PLAYERS = ['north', 'east', 'south', 'west']
TEAMS = {'south_north': ['south', 'north'], 'east_west': ['east', 'west']}
WINNING_TRICKS = 7

def get_team(player):
    """获取玩家所属队伍"""
    for team, members in TEAMS.items():
        if player in members:
            return team
    return None

def get_teammate(player):
    """获取搭档"""
    for team, members in TEAMS.items():
        if player in members:
            return [m for m in members if m != player][0]
    return None

def get_legal_cards(hand, lead_suit):
    """获取合法的出牌列表"""
    if not lead_suit:
        return hand[:]  # 引导时可以出任意牌

    # 检查是否有同花色牌
    same_suit = [card for card in hand if get_suit(card) == lead_suit]
    if same_suit:
        return same_suit
    return hand[:]  # 无同花色时可以出任意牌

def determine_trick_winner(trick, trump_suit, lead_suit):
    """判断墩的赢家"""
    winning_card = None
    winning_player = None

    for player, card in trick.items():
        if winning_card is None:
            winning_card = card
            winning_player = player
            continue

        card_suit = get_suit(card)
        winning_suit = get_suit(winning_card)

        # 1. 如果出王牌
        if card_suit == trump_suit:
            if winning_suit != trump_suit:
                # 王牌 beats 非王牌
                winning_card = card
                winning_player = player
            else:
                # 都是王牌，比较大小
                if get_rank_ace_high(card) > get_rank_ace_high(winning_card):
                    winning_card = card
                    winning_player = player
        # 2. 如果跟的是引导花色（且赢家不是王牌）
        elif card_suit == lead_suit and winning_suit != trump_suit:
            if get_rank_ace_high(card) > get_rank_ace_high(winning_card):
                winning_card = card
                winning_player = player
        # 3. 其他情况（非王牌非引导花色）不赢

    return winning_player

def get_play_order(leader):
    """获取出牌顺序（从引导者开始）"""
    leader_idx = PLAYERS.index(leader)
    return PLAYERS[leader_idx:] + PLAYERS[:leader_idx]

def new_game(session):
    """初始化新游戏"""
    session_id = session.get('session_id', '')

    # 创建并洗牌
    deck = make_deck()
    random.shuffle(deck)

    # 王牌由牌库的最后一张牌决定（发牌前）
    trump_card = deck[-1]
    trump_suit = get_suit(trump_card)

    # 发牌
    hands = {
        'north': sorted(deck[0:13], key=lambda c: (get_suit(c), get_rank_ace_high(c))),
        'east': sorted(deck[13:26], key=lambda c: (get_suit(c), get_rank_ace_high(c))),
        'south': sorted(deck[26:39], key=lambda c: (get_suit(c), get_rank_ace_high(c))),
        'west': sorted(deck[39:52], key=lambda c: (get_suit(c), get_rank_ace_high(c))),
    }

    session['game_state'] = {
        'players': {'north': '电脑-北', 'south': '玩家', 'east': '电脑-东', 'west': '电脑-西'},
        'hands': hands,
        'trump_suit': trump_suit,
        'trump_suit_name': get_suit_name(trump_suit),
        'stop_type': 'new_trick',
        'leader': 'north',  # 首攻由北家开始
        'current_trick': {},
        'tricks': [],
        'scores': {'south_north': 0, 'east_west': 0},
        'message': '点击"新一墩"开始游戏',
        'message_class': 'info-message',
        'played_cards': [],  # 记录已出的牌
    }

def ai_select_card(hand, current_trick, trump_suit, lead_suit, tricks_history, player):
    """AI 选择出牌 - 高级策略"""
    legal_cards = get_legal_cards(hand, lead_suit)

    if not legal_cards:
        return None

    if len(legal_cards) == 1:
        return legal_cards[0]

    teammate = get_teammate(player)

    # 引导时的策略
    if not current_trick:
        return ai_lead_card(hand, legal_cards, trump_suit, tricks_history, player)

    # 跟牌时的策略
    return ai_follow_card(legal_cards, current_trick, trump_suit, lead_suit, player, teammate)

def ai_lead_card(hand, legal_cards, trump_suit, tricks_history, player):
    """AI 引导出牌策略"""
    teammate = get_teammate(player)

    # 策略1: 如果有王牌且较多，先出王牌消耗对手
    trump_cards = [c for c in hand if get_suit(c) == trump_suit]
    if len(trump_cards) >= 4:
        # 出最大的王牌
        return max(trump_cards, key=lambda c: get_rank_ace_high(c))

    # 策略2: 出非王牌的花色中的大牌
    non_trump = [c for c in legal_cards if get_suit(c) != trump_suit]
    if non_trump:
        # 按花色分组
        by_suit = {}
        for card in non_trump:
            suit = get_suit(card)
            if suit not in by_suit:
                by_suit[suit] = []
            by_suit[suit].append(card)

        # 优先出短套（只有1-2张的花色）
        for suit, cards in by_suit.items():
            if len(cards) == 1:
                return cards[0]

        # 出最大的非王牌
        return max(non_trump, key=lambda c: get_rank_ace_high(c))

    # 策略3: 只能出王牌时，出最小的
    if trump_cards:
        return min(trump_cards, key=lambda c: get_rank_ace_high(c))

    # 兜底：返回 legal_cards 中的第一张
    return legal_cards[0] if legal_cards else None

def ai_follow_card(legal_cards, current_trick, trump_suit, lead_suit, player, teammate):
    """AI 跟牌策略"""
    # 检查搭档是否已经赢了这墩
    teammate_winning = False
    if teammate in current_trick:
        teammate_card = current_trick[teammate]
        # 简单判断：搭档的牌是否可能是最大的
        teammate_winning = True
        for p, c in current_trick.items():
            if p != teammate:
                if get_suit(c) == get_suit(teammate_card):
                    if get_rank_ace_high(c) > get_rank_ace_high(teammate_card):
                        teammate_winning = False
                        break
                elif get_suit(c) == trump_suit and get_suit(teammate_card) != trump_suit:
                    teammate_winning = False
                    break

    # 检查对手是否已经出了大牌
    opponent_winning = False
    for p, c in current_trick.items():
        if p != player and p != teammate:
            if get_suit(c) == trump_suit:
                opponent_winning = True
                break
            if get_suit(c) == lead_suit:
                # 对手出了引导花色的大牌
                opponent_winning = True
                break

    # 如果搭档正在赢这墩，出小牌
    if teammate_winning:
        return min(legal_cards, key=lambda c: get_rank_ace_high(c))

    # 有同花色牌时
    same_suit = [c for c in legal_cards if get_suit(c) == lead_suit]
    if same_suit:
        # 尝试出最大的牌来赢墩
        max_card = max(same_suit, key=lambda c: get_rank_ace_high(c))
        # 检查是否能赢
        can_win = True
        for p, c in current_trick.items():
            if get_suit(c) == lead_suit and get_rank_ace_high(c) > get_rank_ace_high(max_card):
                can_win = False
                break

        if can_win:
            return max_card
        else:
            # 不能赢，出最小的
            return min(same_suit, key=lambda c: get_rank_ace_high(c))

    # 无同花色牌时
    trump_cards = [c for c in legal_cards if get_suit(c) == trump_suit]
    non_trump = [c for c in legal_cards if get_suit(c) != trump_suit]

    # 如果对手在赢，尝试用王牌吃
    if opponent_winning and trump_cards:
        # 出最小的王牌
        return min(trump_cards, key=lambda c: get_rank_ace_high(c))

    # 否则垫最小的非王牌
    if non_trump:
        return min(non_trump, key=lambda c: get_rank_ace_high(c))

    # 只能出王牌（如果有的话）
    if trump_cards:
        return min(trump_cards, key=lambda c: get_rank_ace_high(c))

    # 如果没有任何牌，返回 legal_cards 中的第一张（不应该发生）
    return legal_cards[0] if legal_cards else None

def determine_and_update(game_state, lead_suit):
    """判断赢家并更新游戏状态"""
    winner = determine_trick_winner(
        game_state['current_trick'],
        game_state['trump_suit'],
        lead_suit
    )

    winner_team = get_team(winner)
    game_state['scores'][winner_team] += 1

    game_state['tricks'].append({
        'cards': game_state['current_trick'].copy(),
        'winner': winner
    })

    if game_state['scores'][winner_team] >= WINNING_TRICKS:
        game_state['stop_type'] = 'game_over'
        if winner_team == 'south_north':
            game_state['message'] = '恭喜！你和搭档赢得了比赛！'
            game_state['message_class'] = 'success-message'
        else:
            game_state['message'] = '很遗憾，对手赢得了比赛。'
            game_state['message_class'] = 'error-message'
    else:
        game_state['stop_type'] = 'new_trick'
        game_state['leader'] = winner
        game_state['message'] = f'{game_state["players"][winner]}赢得此墩！点击"新一墩"继续'
        game_state['message_class'] = 'info-message'

def game_update(session, action):
    """处理游戏更新"""
    game_state = session.get('game_state')
    if not game_state:
        return new_game(session)

    stop_type = game_state['stop_type']

    # 游戏结束状态
    if stop_type == 'game_over':
        if action == 'new_game':
            return new_game(session)
        return

    # 新一墩开始
    if action == 'new_trick':
        if stop_type == 'new_trick':
            game_state['current_trick'] = {}
            leader = game_state['leader']

            # 获取出牌顺序
            play_order = get_play_order(leader)
            south_idx = play_order.index('south')

            # 让所有在 South 之前的 AI 出牌
            for i in range(south_idx):
                player = play_order[i]
                # 第一个 AI（leader）引导出牌，其他 AI 跟牌
                if i == 0:
                    lead_suit = None  # 引导时无花色限制
                else:
                    lead_suit = get_suit(game_state['current_trick'][leader])

                ai_card = ai_select_card(
                    game_state['hands'][player],
                    game_state['current_trick'],
                    game_state['trump_suit'],
                    lead_suit,
                    game_state['tricks'],
                    player
                )
                # 如果 AI 没有选择牌，强制选择第一张
                if not ai_card and game_state['hands'][player]:
                    ai_card = game_state['hands'][player][0]
                if ai_card:
                    game_state['hands'][player].remove(ai_card)
                    game_state['current_trick'][player] = ai_card
                    game_state['played_cards'].append(ai_card)

            # 设置状态
            if south_idx == 0:
                # South 是第一个出牌的
                game_state['stop_type'] = 'lead_card'
                game_state['message'] = '请出一张牌（引导）'
            else:
                # 已经有 AI 出牌了
                game_state['stop_type'] = 'follow_card'
                last_ai = play_order[south_idx - 1]
                game_state['message'] = f'{game_state["players"][last_ai]}出了 {game_state["current_trick"][last_ai]}，请出牌'

            game_state['message_class'] = 'info-message'
        return

    # 出牌动作（人类玩家）
    if action.startswith('play/'):
        card_str = action[5:]

        if stop_type == 'lead_card':
            # 人类玩家引导出牌
            if card_str in game_state['hands']['south']:
                game_state['hands']['south'].remove(card_str)
                game_state['current_trick']['south'] = card_str
                game_state['played_cards'].append(card_str)

                # 获取出牌顺序
                play_order = get_play_order('south')

                # South 之后的 AI 出牌
                for i in range(1, 4):
                    player = play_order[i]
                    ai_card = ai_select_card(
                        game_state['hands'][player],
                        game_state['current_trick'],
                        game_state['trump_suit'],
                        get_suit(game_state['current_trick']['south']),
                        game_state['tricks'],
                        player
                    )
                    # 如果 AI 没有选择牌，强制选择第一张
                    if not ai_card and game_state['hands'][player]:
                        ai_card = game_state['hands'][player][0]
                    if ai_card:
                        game_state['hands'][player].remove(ai_card)
                        game_state['current_trick'][player] = ai_card
                        game_state['played_cards'].append(ai_card)

                # 判断赢家并更新状态
                determine_and_update(game_state, get_suit(game_state['current_trick']['south']))

        elif stop_type == 'follow_card':
            # 人类玩家跟牌
            lead_suit = get_suit(game_state['current_trick'][game_state['leader']])
            legal_cards = get_legal_cards(game_state['hands']['south'], lead_suit)

            if card_str in legal_cards:
                game_state['hands']['south'].remove(card_str)
                game_state['current_trick']['south'] = card_str
                game_state['played_cards'].append(card_str)

                # 获取出牌顺序
                play_order = get_play_order(game_state['leader'])
                south_idx = play_order.index('south')

                # South 之后的 AI 出牌
                for i in range(south_idx + 1, 4):
                    player = play_order[i]
                    ai_card = ai_select_card(
                        game_state['hands'][player],
                        game_state['current_trick'],
                        game_state['trump_suit'],
                        lead_suit,
                        game_state['tricks'],
                        player
                    )
                    # 如果 AI 没有选择牌，强制选择第一张
                    if not ai_card and game_state['hands'][player]:
                        ai_card = game_state['hands'][player][0]
                    if ai_card:
                        game_state['hands'][player].remove(ai_card)
                        game_state['current_trick'][player] = ai_card
                        game_state['played_cards'].append(ai_card)

                # 判断赢家并更新状态
                determine_and_update(game_state, lead_suit)
