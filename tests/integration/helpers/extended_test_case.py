from unittest import TestCase


class ExtendedTestCase(TestCase):
    def _list_as_dict(self, input_list, item_key):
        """Transform a list into a dictionary where each
        key is some *unique* value (itemKey) for each
        item/dictionary in the list
        Args:
            input_list: The list to transform
            item_key: The unique key for which the output
                dict's keys will be defined from values
                in the list
        """
        transformed = {}
        for item in input_list:
            transformed[item[item_key]] = item

        return transformed

    def assertListOfDictsEqual(
        self,
        actual_list,
        expected_list,
        item_key,
        message=None
    ):
        """Given an two lists of dictionaries (where the dictionary's key is
        some *unique* value (item_key) for each item/dictionary in the list),
        assert that the list contains every dictionary with the pertinent
        values for value_key.
        Args:
            actual_list: The first list of dicts to compare.
            expected_list: The second list to dicts compare.
            item_key: The (unique) key in each dict used to compare between
                the lists.
        """
        expected_list_as_dict = self._list_as_dict(expected_list, item_key)
        value_keys = list(expected_list[0].keys())
        value_keys.remove(item_key)

        for item in actual_list:
            for value_key in value_keys:
                try:
                    self.assertEqual(item[value_key],
                                    expected_list_as_dict[item[item_key]][value_key], msg=message)
                except Exception as e:
                    self.fail('{} - {}'.format(message, e))

    def assertDictsMostlyEqual(
        self,
        actual_dict,
        expected_dict,
        fuzzy_keys=[],
        ignored_keys=[]
    ):
        """Give two dictionaries, compare the dictionaries, permitting specific keys
        to be almost equal and other specific keys to be ignored entirely.
        Args:
            actual_dict: The first dict to compare
            expected_dict: The second dict to compare
            fuzzy_keys: A list of specific keys to only compare for near-equality
            ignored_keys: A list of keys that are not compared at all (e.g., to be
                          examined separately)
        """
        all_keys = list(expected_dict.keys())
        for key in all_keys:
            if ignored_keys.count(key) > 0:
                continue
            elif fuzzy_keys.count(key) > 0:
                try:
                    if len(expected_dict[key].pattern) > 0:
                        self.assertGreater(len(expected_dict[key].findall(actual_dict[key])), 0)
                except AttributeError:
                    try:
                        self.assertAlmostEqual(actual_dict[key], expected_dict[key], msg='Key {} is not almost equal'.format(key))
                    except KeyError:
                        self.fail(msg='Actual result does not contain key `{}`'.format(key))
                except KeyError:
                    self.fail(msg='Actual result does not contain key `{}`'.format(key))
            else:
                try:
                    self.assertEqual(actual_dict[key], expected_dict[key], msg='Key {} is not equal'.format(key))
                except KeyError:
                    self.fail(msg='Actual result does not contain key `{}`'.format(key))
