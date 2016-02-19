import os
import shutil
from collections import defaultdict

class Dictionary(object):
    topo_template = '<State> {cur_state} <PdfClass> {cur_state} <Transition> {cur_state} 0.75 <Transition> {next_state} 0.25 </State>'
    topo_sil_template = '<State> {cur_state} <PdfClass> {cur_state} {transitions} </State>'
    topo_transition_template = '<Transition> {} {}'
    positions = ["_B", "_E", "_I", "_S"]

    @staticmethod
    def read(filename):
        pass

    def __init__(self, input_path, output_directory, oov_code = '<unk>',
                    position_dependent_phones = True, num_sil_states = 5,
                    num_nonsil_states = 3, shared_silence_phones = False,
                    sil_prob = 0.5):
        self.output_directory = output_directory
        if not os.path.exists(self.phones_dir):
            os.makedirs(self.phones_dir, exist_ok = True)
        self.num_sil_states = num_sil_states
        self.num_nonsil_states = num_nonsil_states
        self.shared_silence_phones = shared_silence_phones
        self.sil_prob = sil_prob
        self.oov_code = oov_code
        self.position_dependent_phones = position_dependent_phones

        self.words = defaultdict(list)
        self.nonsil_phones = set()
        self.sil_phones = set(['sil', 'spn'])
        self.optional_silence = 'sil'
        self.disambig = set()
        self.graphemes = set()
        with open(input_path, 'r', encoding = 'utf8') as inf:
            for line in inf:
                line = line.strip()
                if not line:
                    continue
                line = line.split()
                word = line.pop(0).lower()
                self.graphemes.update(word)
                pron = line
                self.words[word].append(pron)
                self.nonsil_phones.update(pron)
        self.words['!SIL'].append(['sil'])
        self.words[self.oov_code].append(['spn'])
        self.phone_mapping = {}
        i = 0
        self.phone_mapping['<eps>'] = i
        for p in sorted(self.sil_phones) + sorted(self.nonsil_phones) + sorted(self.disambig):
            if self.position_dependent_phones:
                if p in self.sil_phones:
                    i += 1
                    self.phone_mapping[p] = i
                for pos in self.positions:
                    i += 1
                    self.phone_mapping[p+pos] = i
            else:
                i += 1
                self.phone_mapping[p] = i

        self.words_mapping = {}
        i = 0
        self.words_mapping['<eps>'] = i
        for w in sorted(self.words.keys()):
            i += 1
            self.words_mapping[w] = i

        self.words_mapping['#0'] = i + 1
        self.words_mapping['<s>'] = i + 2
        self.words_mapping['</s>'] = i + 3

    @property
    def phones_dir(self):
        return os.path.join(self.output_directory, 'phones')

    @property
    def phones(self):
        return self.sil_phones & self.nonsil_phones

    def write(self):
        self._write_lexicon()
        self._write_lexiconp()

        self._write_graphemes()
        self._write_phone_map_file()
        self._write_phone_sets()
        self._write_phone_symbol_table()
        self._write_topo()
        self._write_word_boundaries()
        self._write_word_file()

    def _write_graphemes(self):
        outfile = os.path.join(self.output_directory, 'graphemes.txt')
        with open(outfile, 'w', encoding = 'utf8') as f:
            for char in sorted(self.graphemes):
                f.write(char + '\n')

    def _write_lexicon(self):
        outfile = os.path.join(self.output_directory, 'lexicon.txt')
        with open(outfile, 'w', encoding = 'utf8') as f:
            for w in sorted(self.words.keys()):
                for p in sorted(self.words[w]):
                    phones = [x for x in p]
                    if self.position_dependent_phones:
                        if len(phones) == 1:
                            phones[0] += '_S'
                        else:
                            for i in range(len(phones)):
                                if i == 0:
                                    phones[i] += '_B'
                                elif i == len(phones) - 1:
                                    phones[i] += '_E'
                                else:
                                    phones[i] += '_I'
                    phones = ' '.join(phones)
                    f.write('{}\t{}\n'.format(w, phones))

    def _write_lexiconp(self):
        outfile = os.path.join(self.output_directory, 'lexiconp.txt')
        with open(outfile, 'w', encoding = 'utf8') as f:
            for w in sorted(self.words.keys()):
                for p in sorted(self.words[w]):
                    phones = [x for x in p]
                    if self.position_dependent_phones:
                        if len(phones) == 1:
                            phones[0] += '_S'
                        else:
                            for i in range(len(phones)):
                                if i == 0:
                                    phones[i] += '_B'
                                elif i == len(phones) - 1:
                                    phones[i] += '_E'
                                else:
                                    phones[i] += '_I'
                    phones = ' '.join(phones)
                    p = 1.0
                    f.write('{}\t{}\t{}\n'.format(w, p, phones))

    def _write_phone_map_file(self):
        outfile = os.path.join(self.output_directory, 'phone_map.txt')
        with open(outfile, 'w', encoding = 'utf8') as f:
            for sp in self.sil_phones:
                if self.position_dependent_phones:
                    new_phones = [sp+x for x in ['', ''] + self.positions]
                else:
                    new_phones = [sp]
                f.write(' '.join(new_phones) + '\n')
            for nsp in self.nonsil_phones:
                if self.position_dependent_phones:
                    new_phones = [nsp+x for x in [''] + self.positions]
                else:
                    new_phones = [nsp]
                f.write(' '.join(new_phones) + '\n')

    def _write_phone_symbol_table(self):
        outfile = os.path.join(self.output_directory, 'phones.txt')
        with open(outfile, 'w', encoding = 'utf8') as f:
            for p, i in sorted(self.phone_mapping.items(), key = lambda x: x[1]):
                f.write('{} {}\n'.format(p, i))

    def _write_word_boundaries(self):
        boundary_path = os.path.join(self.output_directory, 'phones', 'word_boundary.txt')
        with open(boundary_path, 'w', encoding = 'utf8') as f:
            if self.position_dependent_phones:
                for p in sorted(self.phone_mapping.keys(),
                            key = lambda x: self.phone_mapping[x]):
                    if p == '<eps>':
                        continue
                    cat = 'nonword'
                    if p.endswith('_B'):
                        cat = 'begin'
                    elif p.endswith('_S'):
                        cat = 'singleton'
                    elif p.endswith('_I'):
                        cat = 'internal'
                    elif p.endswith('_E'):
                        cat = 'end'
                    f.write(' '.join([p, cat])+'\n')

    def _write_word_file(self):
        words_path = os.path.join(self.output_directory, 'words.txt')

        with open(words_path, 'w', encoding = 'utf8') as f:
            for w, i in sorted(self.words_mapping.items(), key = lambda x: x[1]):
                f.write('{} {}\n'.format(w, i))

    def _write_topo(self):
        filepath = os.path.join(self.output_directory, 'topo')
        sil_transp = 1 / (self.num_sil_states - 1)
        sil_transp = 1 / (self.num_sil_states - 1)
        initial_transition = [self.topo_transition_template.format(x, sil_transp)
                                for x in range(self.num_sil_states - 1)]
        middle_transition = [self.topo_transition_template.format(x, sil_transp)
                                for x in range(1, self.num_sil_states)]
        final_transition = [self.topo_transition_template.format(self.num_sil_states - 1, 0.75),
                                self.topo_transition_template.format(self.num_sil_states, 0.25)]
        with open(filepath, 'w') as f:
            f.write('<Topology>\n')
            f.write("<TopologyEntry>\n")
            f.write("<ForPhones>\n")
            f.write("{}\n".format(' '.join(self.nonsil_phones)))
            f.write("</ForPhones>\n")
            states = [self.topo_template.format(cur_state = x, next_state = x + 1)
                        for x in range(self.num_nonsil_states)]
            f.write('\n'.join(states))
            f.write("\n<State> {} </State>\n".format(self.num_nonsil_states))
            f.write("</TopologyEntry>\n")

            f.write("<TopologyEntry>\n")
            f.write("<ForPhones>\n")
            f.write("{}\n".format(' '.join(self.sil_phones)))
            f.write("</ForPhones>\n")
            states = []
            for i in range(self.num_sil_states):
                if i == 0:
                    transition = ' '.join(initial_transition)
                elif i == self.num_sil_states - 1:
                    transition = ' '.join(final_transition)
                else:
                    transition = ' '.join(middle_transition)
                states.append(self.topo_sil_template.format(cur_state = i,
                                                transitions = transition))
            f.write('\n'.join(states))
            f.write("\n<State> {} </State>\n".format(self.num_sil_states))
            f.write("</TopologyEntry>\n")
            f.write("</Topology>\n")

    def _write_phone_sets(self):
        sharesplit = ['shared', 'split']
        if self.shared_silence_phones:
            sil_sharesplit = ['not-shared', 'not-split']
        else:
            sil_sharesplit = sharesplit

        sets_file = os.path.join(self.output_directory, 'phones', 'sets.txt')
        roots_file = os.path.join(self.output_directory, 'phones', 'roots.txt')

        phone_silence = os.path.join(self.output_directory, 'phones', 'silence.txt')
        phone_nonsilence = os.path.join(self.output_directory, 'phones', 'nonsilence.txt')


        with open(sets_file, 'w', encoding = 'utf8') as setf, \
                    open(roots_file, 'w', encoding = 'utf8') as rootf:

            #process silence phones
            with open(phone_silence, 'w', encoding = 'utf8') as silf:
                for i, sp in enumerate(self.sil_phones):
                    if self.position_dependent_phones:
                        mapped = [sp+x for x in [''] + self.positions]
                    else:
                        mapped = [sp]
                    setf.write(' '.join(mapped) + '\n')
                    for item in mapped:
                        silf.write(item + '\n')
                    if i == 0:
                        line = sil_sharesplit + mapped
                    else:
                        line = sharesplit + mapped
                    rootf.write(' '.join(line) + '\n')

            #process nonsilence phones
            with open(phone_nonsilence, 'w', encoding = 'utf8') as nonsilf:
                for nsp in sorted(self.nonsil_phones):
                    if self.position_dependent_phones:
                        mapped = [nsp+x for x in  self.positions]
                    else:
                        mapped = [nsp]
                    setf.write(' '.join(mapped) + '\n')
                    for item in mapped:
                        nonsilf.write(item + '\n')
                    line = sharesplit + mapped
                    rootf.write(' '.join(line) + '\n')

        shutil.copy(phone_silence, os.path.join(self.output_directory, 'phones', 'context_indep.txt'))

    def _write_extra_questions(self):
        phone_extra = os.path.join(self.phones_dir, 'extra_questions.txt')
        with open(phone_extra, 'w', encoding = 'utf8') as outf:
            sils = []
            for sp in sorted(self.sil_phones):
                if self.position_dependent_phones:
                    mapped = [sp+x for x in ['', ''] + self.positions]
                else:
                    mapped = [sp]
                sils.extend(mapped)
            outf.write(' '.join(sils) + '\n')
            nonsils = []
            for nsp in sorted(self.nonsil_phones):
                if self.position_dependent_phones:
                    mapped = [nsp+x for x in [''] + self.positions]
                else:
                    mapped = [nsp]
                nonsils.extend(mapped)
            outf.write(' '.join(nonsils) + '\n')

            for p in self.positions:
                line = [x + p for x in sorted(self.nonsil_phones)]
                outf.write(' '.join(line) + '\n')
            for p in [''] + self.positions:
                line = [x + p for x in sorted(self.sil_phones)]
                outf.write(' '.join(line) + '\n')
