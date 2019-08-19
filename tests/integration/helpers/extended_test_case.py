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